""" This test verifies Fiemap module functionality. It generates random sparse
files and makes sure FIEMAP returns correct information about the holes. """

# Disable the following pylint recommendations:
#   *  Too many public methods - R0904
# pylint: disable=R0904

import random
import unittest
import itertools

import tests.helpers
from bmaptools import Fiemap

class Error(Exception):
    """ A class for exceptions generated by this test. """
    pass

def _check_ranges(f_image, fiemap, first_block, blocks_cnt,
                  ranges, ranges_type):
    """ This is a helper function for '_do_test()' which compares the correct
    'ranges' list of mapped or unmapped blocks ranges for file object 'f_image'
    with what the Fiemap module reports. The 'ranges_type' argument defines
    whether the 'ranges' list is a list of mapped or unmapped blocks. The
    'first_block' and 'blocks_cnt' define the subset of blocks in 'f_image'
    that should be verified by this function. """

    if ranges_type is "mapped":
        fiemap_iterator = fiemap.get_mapped_ranges(first_block, blocks_cnt)
    elif ranges_type is "unmapped":
        fiemap_iterator = fiemap.get_unmapped_ranges(first_block, blocks_cnt)
    else:
        raise Error("incorrect list type")

    last_block = first_block + blocks_cnt - 1

    # The 'ranges' list contains all ranges, from block zero to the last
    # block. However, we are conducting a test for 'blocks_cnt' of blocks
    # starting from block 'first_block'. Create an iterator which filters
    # those block ranges from the 'ranges' list, that are out of the
    # 'first_block'/'blocks_cnt' file region.
    filter_func = lambda x: x[1] >= first_block and x[0] <= last_block
    ranges_iterator = filter(filter_func, ranges)

    iterator = itertools.izip_longest(ranges_iterator, fiemap_iterator)

    # Iterate over both - the (filtered) 'ranges' list which contains correct
    # ranges and the Fiemap generator, and verify the mapped/unmapped ranges
    # returned by the Fiemap module.
    for correct, check in iterator:

        # The first and the last range of the filtered 'ranges' list may still
        # be out of the limit - correct them in this case
        if correct[0] < first_block:
            correct = (first_block, correct[1])
        if correct[1] > last_block:
            correct = (correct[0], last_block)

        if check[0] > check[1] or check != correct:
            raise Error("bad or unmatching %s range for file '%s': correct " \
                        "is %d-%d, get_%s_ranges(%d, %d) returned %d-%d" \
                        % (ranges_type, f_image.name, correct[0], correct[1],
                           ranges_type, first_block, blocks_cnt,
                           check[0], check[1]))

def _do_test(f_image, mapped, unmapped, buf_size = Fiemap.DEFAULT_BUFFER_SIZE):
    """ Verifiy that Fiemap reports the correct mapped and unmapped areas for
    the 'f_image' file object. The 'mapped' and 'unmapped' lists contain the
    correct ranges. The 'buf_size' argument specifies the internal buffer size
    of the 'Fiemap' class. """

    # Make sure that Fiemap's get_mapped_ranges() returns the same ranges as
    # we have in the 'mapped' list.
    fiemap = Fiemap.Fiemap(f_image, buf_size)

    # Check both 'get_mapped_ranges()' and 'get_unmapped_ranges()' for the
    # entire file.
    first_block = 0
    blocks_cnt = fiemap.blocks_cnt
    _check_ranges(f_image, fiemap, first_block, blocks_cnt, mapped, "mapped")
    _check_ranges(f_image, fiemap, first_block, blocks_cnt, unmapped,
                  "unmapped")

    # Select a random area in the file and repeat the test few times
    for _ in xrange(0, 10):
        first_block = random.randint(0, fiemap.blocks_cnt - 1)
        blocks_cnt = random.randint(1, fiemap.blocks_cnt - first_block)
        _check_ranges(f_image, fiemap, first_block, blocks_cnt, mapped,
                      "mapped")
        _check_ranges(f_image, fiemap, first_block, blocks_cnt, unmapped,
                      "unmapped")

class TestCreateCopy(unittest.TestCase):
    """ The test class for this unit tests. Basically executes the '_do_test()'
    function for different sparse files. """

    @staticmethod
    def test():
        """ The test entry point. Executes the '_do_test()' function for files
        of different sizes, holes distribution and format. """

        # Delete all the test-related temporary files automatically
        delete = True
        # Create all the test-related temporary files in the default directory
        # (usually /tmp).
        directory = None
        # Maximum size of the random files used in this test
        max_size = 16 * 1024 * 1024

        iterator = tests.helpers.generate_test_files(max_size, directory,
                                                     delete)
        for f_image, mapped, unmapped in iterator:
            _do_test(f_image, mapped, unmapped)
            _do_test(f_image, mapped, unmapped, Fiemap.MIN_BUFFER_SIZE)
            _do_test(f_image, mapped, unmapped, Fiemap.MIN_BUFFER_SIZE * 2)
            _do_test(f_image, mapped, unmapped, Fiemap.DEFAULT_BUFFER_SIZE / 2)
            _do_test(f_image, mapped, unmapped, Fiemap.DEFAULT_BUFFER_SIZE * 2)

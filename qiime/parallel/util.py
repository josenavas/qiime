#!/usr/bin/env python
# File created on 07 Jul 2012
from __future__ import division

__author__ = "Greg Caporaso"
__copyright__ = "Copyright 2011, The QIIME project"
__credits__ = ["Greg Caporaso", "Jens Reeder", "Jai Ram Rideout",
               "Daniel McDonald", "Jose Antonio Navas Molina"]
__license__ = "GPL"
__version__ = "1.8.0-dev"
__maintainer__ = "Greg Caporaso"
__email__ = "gregcaporaso@gmail.com"

from qiime.util import load_qiime_config


qiime_config = load_qiime_config()


class ComputeError(Exception):
    pass


def concatenate_files(output_fp, temp_out_fps):
    with open(output_fp, 'w') as out_f:
        for tmp_fp in temp_out_fps:
            with open(tmp_fp, 'U') as in_f:
                for line in in_f:
                    out_f.write('%s\n' % line.strip('\n'))


def merge_files_from_dirs(output_fp, output_dirs, format_str, merge_func):
    """Wraps the concatenate_files function so it can generate the actual list
    of files to concatenate from the directories in output_dirs

    Parameters
    ----------
    output_fp : str
        The path to the output file
    output_dirs : list of str
        The list of directories in which we should search for the files
    format_str : str
        The formatted string of the files that we have to search for. It should
        include any wildcard that glob can parse (e.g. '*')
    merge_func : function
        The function used to merge the results. Signature: f(output_fp, files)
    """
    # Importing here so it is available to the workers
    from glob import glob
    from os.path import join
    files = []
    for out_dir in output_dirs:
        files.extend(glob(join(out_dir, format_str)))
    merge_func(output_fp, files)


def input_fasta_splitter(input_fp, output_dir, num):
    """Splits the input fasta file in num chunks and puts them on output_dir

    Parameters
    ----------
    input_fp : str
        Path to the input fasta file
    output_dir : str
        Path to the output directory. It will be created if it does not exists
    num : int
        Number of chunks in which the input fasta file should be divided

    Returns
    -------
    list of str
        A list of paths to the chunk files
    """
    # Importing here so it becomes available on the workers
    from os.path import exists, basename, splitext, join
    from os import makedirs
    from skbio.parse.sequences import load

    if not exists(output_dir):
        makedirs(output_dir)

    # Generate a prefix for the output files
    prefix = splitext(basename(input_fp))[0]
    fasta_fps = [join(output_dir, '%s.%s.fasta' % (prefix, i))
                 for i in range(num)]
    # Open all the files
    open_files = [open(fp, 'w') for fp in fasta_fps]

    # Write the chunks
    for i, rec in enumerate(load([input_fp])):
        open_files[i % num].write('>%s\n%s\n' % (rec['SequenceID'],
                                                 rec['Sequence']))

    # close all the files
    for of in open_files:
        of.close()

    # Return the list of filepaths
    return fasta_fps


class BufferedWriter():

    """A file like object that delays writing to file without keeping an open
    filehandle

    This class comes useful in scenarios were potentially many open fhs are
    needed (e.g. during splitting of inputs for parallelization). Since
    each OS limits the max number of open fh at any time, we provide a fh like
    class that can be used much like a regular (writable) fh, but without
    keeping the fh open permanently. Using a larger buffer size speeds up the
    program by using less of the expensive open/close IO operations.
    """

    def __init__(self, filename, buf_size=100):
        """
        filename: name of file to write to in append mode

        buf_size: buffer size in chunks. Each write operations counts as one
        chunk.
        """

        if(buf_size < 1):
            raise ValueError("Invalid buf_size. Must be 1 or larger.")

        self.buffer = []
        self.buf_size = buf_size
        self.filename = filename

        # touch the file
        fh = open(self.filename, "w")
        fh.close()

    def __del__(self):
        self._flush()

    def close(self):
        self._flush()

    def write(self, line):
        """write line to BufferedWriter"""

        self.buffer.append(line)
        if (len(self.buffer) > self.buf_size):
            self._flush()

    def _flush(self):
        """Write buffer to file"""

        fh = open(self.filename, "a")
        fh.write("".join(self.buffer))
        fh.close()

        self.buffer = []

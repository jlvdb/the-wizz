#!/usr/bin/env python3

"""This program is a convinience method for computing the clustering redshift
recovery for the full unknown sample stored in pair_maker.py. In this mode
The-wiZZ can behave more like recovery codes of yore. This could be useful, for
instance in surveys where only a single observed band pass is available (e.g. a
radio survey). This program does not allow for the use of a weight for
the unknown objects. For that one must use the regular pdf_maker.py program.
The same input parameters are used as pdf_maker.py however some are not used in
this program (e.g. n_process, unknown_weight_name).
"""

import numpy as np

from the_wizz import core_utils
from the_wizz import input_flags
from the_wizz import pdf_maker_utils


if __name__ == "__main__":
    print("")
    print("The-wiZZ has begun conjuring: running pdf maker full sample...")
    # First we parse the command line for arguments as usual. See
    # input_flags.py for a full list of input arguments.
    args = input_flags.parse_input_pdf_args()
    input_flags.print_args(args)
    if args.unknown_weight_name is not None:
        print("WARNING: A weight name, %s has been specified for the unknown "
              "sample. This is not possible with this code. If this was a "
              "mistake, ignore this message and continue, else kill this "
              "process and use pdf_maker.py instead." %
              args.unknown_weight_name)
        print("\tContinuing...")
    # Load the file containing all matched pairs of spectroscopic and
    # photometric objects.
    print("Loading files...")
    hdf5_pair_file = core_utils.file_checker_loader(args.input_pair_hdf5_file)
    unknown_data = core_utils.file_checker_loader(args.unknown_sample_file)
    # Load the spectroscopic data from the HDF5 data file.
    print("Preloading reference data...")
    pdf_maker = pdf_maker_utils.PDFMaker(
        hdf5_pair_file, args)
    if pdf_maker.reference_redshift_array.max() < args.z_max:
        print("WARNING: requested z_max is greater than available reference "
              "redshifts.")
    # Now we figure out what kind of redshift binning we would like to have.
    # This will be one of the largest impacts on the signal to noise of the
    # measurement. Some rules of thumb are:
    #     The narrower bins are in redshift the better. You are measuring a
    # correlation, the narrower the bin size in comoving distance the more
    # correlated things will be and thus increase the amplitude. Aka use
    # Groth/Pebbles[sic] scaling to your advantage.
    #     For a spectroscopic sample that is selected for a specific redshift
    # range with few galaxies outside that range (eg DEEP2), adaptive binning
    # is recommended. This will keep a equal number spectra per redshift bin.
    # A good rule is to try to have about 100 spectra per redshift bin for max
    # signal to noise.
    #     Linear binning is provided as a curtesy and is not nesassarly
    # recommended. It will not give the best signal to noise compared to
    # adaptive and has the same draw backs as adaptive is that the bias could
    # be changing oddly from bin to bin. It is recommended that the user try
    # adaptive and comoving spaced bins for the best results. Comoving returns
    # bins that are of equal comoving distance from the line of sight. We also
    # provide binning in equal ln(1 + z). This is for people who want a
    # comoving like binning but without the dependece on cosmology. It also
    # has the convienent property of giving errors that can be more easlily
    # compared the usual simga/(1 + z) error.
    print("Creating bins...")
    if args.z_binning_type == 'linear':
        z_bin_edge_array = pdf_maker_utils._create_linear_redshift_bin_edges(
            args.z_min, args.z_max, args.z_n_bins)
    elif args.z_binning_type == 'adaptive':
        z_bin_edge_array = pdf_maker_utils._create_adaptive_redshift_bin_edges(
            args.z_min, args.z_max, args.z_n_bins,
            pdf_maker.reference_redshift_array)
    elif args.z_binning_type == 'comoving':
        z_bin_edge_array = pdf_maker_utils._create_comoving_redshift_bin_edges(
            args.z_min, args.z_max, args.z_n_bins)
    elif args.z_binning_type == 'logspace':
        z_bin_edge_array = pdf_maker_utils._create_logspace_redshift_bin_edges(
            args.z_min, args.z_max, args.z_n_bins)
    else:
        print("Requested binning name invalid. Valid types are:")
        print("\tlinear: linear binning in redshift")
        print("\tadaptive: constant reference objects per redshift bin")
        print("\tcomoving: linear binning in comoving distance")
        print("Retunning linear binning...")
        z_bin_edge_array = pdf_maker_utils._create_linear_redshift_bin_edges(
            args.z_min, args.z_max, args.z_n_bins)
    # This is where the heavy lifting happens. We create our PDF maker object
    # which will hold the pair file for use, calculate the over density per
    # redshift bin, and also store intermediary results for later use.
    # Before we can estimate the PDF, we must mask for the objects we want
    # to estimate the redshit of. These objects can be color selected,
    # photo-z selected, or any other object selection you would like. The code
    # line below turns the array of indices in the hdf5 pair file, into a
    # single density estimate around the reference object.
    print("Collapsing indices...")
    pdf_maker_utils.collapse_full_sample(
        hdf5_pair_file['data'], pdf_maker, unknown_data, args)
    # Before we calculated the pdfs, we want to know what the over densities
    # are in each of the regions calculated on the area we consider.
    print("Calculating region densities...")
    pdf_maker.compute_region_densities(z_bin_edge_array, args.z_max)
    if args.output_region_pickle_file is not None:
        pdf_maker.write_region_densities(args.output_region_pickle_file, args)
    # Now that we've "collapsed" the estimate around the reference object we
    # need to bin up the results in redshift and create our final PDF.
    print("Calculating pdf...")
    if args.bootstrap_samples is None:
        pdf_maker.compute_pdf_bootstrap(args.n_bootstrap)
    else:
        bootstrap_region_array = np.loadtxt(args.bootstrap_samples,
                                            dtype=np.int_)
        pdf_maker._compute_pdf_bootstrap(bootstrap_region_array)
    # Write individual bootstraps to file.
    if args.output_bootstraps_file is not None:
        pdf_maker.write_bootstrap_samples_to_ascii(args.output_bootstraps_file,
                                                   args)
    # Now that we have the results. We just need to write them to file and we
    # are done.
    print("Writing...")
    output_file = core_utils.create_ascii_file(args.output_pdf_file_name, args)
    pdf_maker.write_pdf_to_ascii(output_file)
    output_file.close()
    print("Done!")

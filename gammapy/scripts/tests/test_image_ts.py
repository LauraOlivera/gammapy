# Licensed under a 3-clause BSD style license - see LICENSE.rst
from __future__ import absolute_import, division, print_function, unicode_literals

import json
import numpy as np
from numpy.testing.utils import assert_allclose
from ...utils.testing import requires_dependency, requires_data
from ...detect import TSMapResult
from ...datasets import load_poisson_stats_image
from ..image_ts import image_ts_main
from astropy.io import fits
from ...datasets.core import gammapy_extra


def create_test_input_file(input_filename, data):
    maps = [data['counts'], data['background'], data['exposure']]
    maps_names = ['On', 'Background', 'ExpGammaMap']

    hdu_list = fits.HDUList()
    for map_field, name in zip(maps, maps_names):
        hdu = fits.ImageHDU(data=map_field, header=data["header"], name=name)
        hdu_list.append(hdu)
    hdu_list.writeto(input_filename)


def init_psf_file(tmpdir):
    psf_filename = str(tmpdir / 'psf.json')

    psf_pars = dict()
    psf_pars['psf1'] = dict(ampl=0.0254647908947033, fwhm=5.8870501125773735)
    psf_pars['psf2'] = dict(ampl=0, fwhm=1E-5)
    psf_pars['psf3'] = dict(ampl=0, fwhm=1E-5)
    json.dump(psf_pars, open(psf_filename, "w"))

    return psf_filename


@requires_dependency('scipy')
@requires_dependency('skimage')
@requires_data('gammapy-extra')
def test_command_line_gammapy_image_ts(tmpdir):
    """Minimal test of gammapy_image_ts using testcase that
    guaranteed to work with compute_ts_map"""
    data = load_poisson_stats_image(extra_info=True)
    data['exposure'] = np.ones(data['counts'].shape) * 1E12

    input_filename = str(tmpdir / 'input_all.fits.gz')
    create_test_input_file(input_filename, data)

    psf_filename = init_psf_file(tmpdir)

    output_filename = str(tmpdir / "output.fits")
    output_filename_without_nan = str(tmpdir / "output_without_nan.fits")
    expected_filename = str(gammapy_extra.dir /
                         'test_datasets/unbundled/poisson_stats_image/expected_output.fits')

    scales_test_list = ['0.000', '0.050', '0.100', '0.200']
    image_ts_main([input_filename,
                   output_filename,
                   "--psf",
                   psf_filename,
                   "--scales",
                   scales_test_list[0],
                   scales_test_list[1],
                   scales_test_list[2],
                   scales_test_list[3]])

    for scale_test in scales_test_list:
        output_filename_ = output_filename.replace('.fits', '_{0}.fits'.format(scale_test))
        expected_filename_ = expected_filename.replace('.fits', '_{0}.fits'.format(scale_test))

        read_console = TSMapResult.read(output_filename_)
        for name, order in zip(['ts', 'sqrt_ts', 'amplitude', 'niter'], [1, 1, 1, 0]):
                read_console[name] = np.nan_to_num(read_console[name])
        output_filename_without_nan_ = output_filename_without_nan.replace('.fits',
                                                                           '_{0}.fits'.format(scale_test))
        read_console.write(output_filename_without_nan_, header=data['header'])

        expected_hdu = fits.open(expected_filename_)[0]
        console_hdu = fits.open(output_filename_without_nan_)[0]

        assert_allclose(expected_hdu.data, console_hdu.data, rtol=1e-2, atol=1e-15)

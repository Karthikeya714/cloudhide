# Sample Carrier Images

Three PNG images for demoing CloudHide's carrier analysis and hiding pipeline
without needing to source your own images first.

| File | Description | Expected carrier suitability |
|---|---|---|
| `sample_noise_512.png` | 512x512 uniform random RGB noise | High — near-maximum Shannon entropy and edge density, so LSB changes blend into existing noise |
| `sample_textured_512.png` | 512x512 synthetic wave pattern with noise overlay | Medium — moderate entropy, more representative of a real photograph |
| `sample_gradient_512.png` | 512x512 smooth color gradient | Low — very low entropy and edge density; included to show the scoring algorithm correctly penalizing flat images |

Upload all three via the "Hide File" page or `POST /api/carriers/upload` to
see CloudHide's adaptive carrier ranking pick the noisy/textured images over
the gradient one, with an explanation for each score.

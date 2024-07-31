{buildPythonPackage, fetchurl, nixpkgs, python}: rec {
  packages = rec {
    urllib3 = buildPythonPackage {
      pname = "urllib3";
      version = "2.2.2";
      format="wheel";
      src = fetchurl {
        url="https://files.pythonhosted.org/packages/ca/1c/89ffc63a9605b583d5df2be791a27bc1a42b7c32bab68d3c8f2f73a98cd4/urllib3-2.2.2-py3-none-any.whl";
        hash="sha256-pEiy9k1oYVVGgDfhrOny0hmXduF/CkZhBIDTEfc+NHI=";
      };
      doCheck = false;
    };
    wheel = buildPythonPackage {
      pname = "wheel";
      version = "0.43.0";
      format="wheel";
      src = fetchurl {
        url="https://files.pythonhosted.org/packages/7d/cd/d7460c9a869b16c3dd4e1e403cce337df165368c71d6af229a74699622ce/wheel-0.43.0-py3-none-any.whl";
        hash="sha256-VcVwQF8UJjDGufcv4J2bZ88Ud/z1Q65bjcsfW3N32oE=";
      };
      doCheck = false;
    };
    charset-normalizer = buildPythonPackage {
      pname = "charset-normalizer";
      version = "3.3.2";
      format="wheel";
      src = fetchurl {
        url="https://files.pythonhosted.org/packages/28/76/e6222113b83e3622caa4bb41032d0b1bf785250607392e1b778aca0b8a7d/charset_normalizer-3.3.2-py3-none-any.whl";
        hash="sha256-Pk0fZYcyLSeIg2qZxpBi+7CRMx7JQOAtEtF5wdU+Jfw=";
      };
      doCheck = false;
    };
    setuptools = buildPythonPackage {
      pname = "setuptools";
      version = "71.1.0";
      format="wheel";
      src = fetchurl {
        url="https://files.pythonhosted.org/packages/51/a0/ee460cc54e68afcf33190d198299c9579a5eafeadef0016ae8563237ccb6/setuptools-71.1.0-py3-none-any.whl";
        hash="sha256-M4dP3FmzGIMEsufIDZApCX6jFicYCJb7VJxXjOuKCFU=";
      };
      doCheck = false;
    };
    typing-extensions = buildPythonPackage {
      pname = "typing-extensions";
      version = "4.12.2";
      format="wheel";
      src = fetchurl {
        url="https://files.pythonhosted.org/packages/26/9f/ad63fc0248c5379346306f8668cda6e2e2e9c95e01216d2b8ffd9ff037d0/typing_extensions-4.12.2-py3-none-any.whl";
        hash="sha256-BOXKA1Hg8/hcaFOVQHLfZZ0NE/rDJNAHIxa2fXeUcA0=";
      };
      doCheck = false;
    };
    meson = buildPythonPackage {
      pname = "meson";
      version = "1.5.0";
      format="wheel";
      src = fetchurl {
        url="https://files.pythonhosted.org/packages/c4/cd/47e45d3abada2e1edb9e2ca9334be186d2e7f97a01b09b5b82799c4d7bd3/meson-1.5.0-py3-none-any.whl";
        hash="sha256-UrNPSQO4gt9SrQ1TMUbUuZLAGOp3OZ+CVXlzdnKueyA=";
      };
      doCheck = false;
    };
    exceptiongroup = buildPythonPackage {
      pname = "exceptiongroup";
      version = "1.2.2";
      format="wheel";
      src = fetchurl {
        url="https://files.pythonhosted.org/packages/02/cc/b7e31358aac6ed1ef2bb790a9746ac2c69bcb3c8588b41616914eb106eaf/exceptiongroup-1.2.2-py3-none-any.whl";
        hash="sha256-MRG50THCOL7C+PUW4SPhS6JDVj+xNdP+iFmQWFqneVs=";
      };
      doCheck = false;
    };
    pygments = buildPythonPackage {
      pname = "pygments";
      version = "2.18.0";
      format="wheel";
      src = fetchurl {
        url="https://files.pythonhosted.org/packages/f7/3f/01c8b82017c199075f8f788d0d906b9ffbbc5a47dc9918a945e13d5a2bda/pygments-2.18.0-py3-none-any.whl";
        hash="sha256-uOasoFI/Ordv7lF5nEiOOHgqwG6vz5XnuoMphcjnsTo=";
      };
      doCheck = false;
    };
    h11 = buildPythonPackage {
      pname = "h11";
      version = "0.14.0";
      format="wheel";
      src = fetchurl {
        url="https://files.pythonhosted.org/packages/95/04/ff642e65ad6b90db43e668d70ffb6736436c7ce41fcc549f4e9472234127/h11-0.14.0-py3-none-any.whl";
        hash="sha256-4/5KxLhRxGjMg2PVANtSwurQNgIHIwJKEJ03NG76p2E=";
      };
      doCheck = false;
    };
    httpcore = buildPythonPackage {
      pname = "httpcore";
      version = "1.0.5";
      format="wheel";
      src = fetchurl {
        url="https://files.pythonhosted.org/packages/78/d4/e5d7e4f2174f8a4d63c8897d79eb8fe2503f7ecc03282fee1fa2719c2704/httpcore-1.0.5-py3-none-any.whl";
        hash="sha256-Qh8YusJIsl0xDzys0ZjVW45hJcEHeXtgn/m3prp5kbU=";
      };
      dependencies = with packages;
      with buildPackages;
      [certifi h11];
      doCheck = false;
    };
    requests = buildPythonPackage {
      pname = "requests";
      version = "2.32.3";
      format="wheel";
      src = fetchurl {
        url="https://files.pythonhosted.org/packages/f9/9b/335f9764261e915ed497fcdeb11df5dfd6f7bf257d4a6a2a686d80da4d54/requests-2.32.3-py3-none-any.whl";
        hash="sha256-cHYc/gPHc86yKqL2cbR1eXYUUXXN/KA4wCZU0GHW3MY=";
      };
      dependencies = with packages;
      with buildPackages;
      [certifi charset-normalizer idna urllib3];
      doCheck = false;
    };
    pip = buildPythonPackage {
      pname = "pip";
      version = "24.1.2";
      format="wheel";
      src = fetchurl {
        url="https://files.pythonhosted.org/packages/e7/54/0c1c068542cee73d8863336e974fc881e608d0170f3af15d0c0f28644531/pip-24.1.2-py3-none-any.whl";
        hash="sha256-fNIH7tTGCw9BG0RM0UZBmP4YZnHDI7bNbUM+2A/J0kc=";
      };
      doCheck = false;
    };
    mdurl = buildPythonPackage {
      pname = "mdurl";
      version = "0.1.2";
      format="wheel";
      src = fetchurl {
        url="https://files.pythonhosted.org/packages/b3/38/89ba8ad64ae25be8de66a6d463314cf1eb366222074cfda9ee839c56a4b4/mdurl-0.1.2-py3-none-any.whl";
        hash="sha256-hACKQeUWFaSfyZZhkf+RUJ48QLk5F25kP9UKXCGWuPg=";
      };
      doCheck = false;
    };
    pyproject-metadata = buildPythonPackage {
      pname = "pyproject-metadata";
      version = "0.8.0";
      format="wheel";
      src = fetchurl {
        url="https://files.pythonhosted.org/packages/aa/5f/bb5970d3d04173b46c9037109f7f05fc8904ff5be073ee49bb6ff00301bc/pyproject_metadata-0.8.0-py3-none-any.whl";
        hash="sha256-rYWNRI4dOh+0CKxbrJ6ndD56i7tHLyaTqqM00ttC9SY=";
      };
      dependencies = with packages;
      with buildPackages;
      [packaging];
      doCheck = false;
    };
    markdown-it-py = buildPythonPackage {
      pname = "markdown-it-py";
      version = "3.0.0";
      format="wheel";
      src = fetchurl {
        url="https://files.pythonhosted.org/packages/42/d7/1ec15b46af6af88f19b8e5ffea08fa375d433c998b8a7639e76935c14f1f/markdown_it_py-3.0.0-py3-none-any.whl";
        hash="sha256-NVIWhFxgvZYjLNjYxA6Pl2XMhvRogOQ6j9ItwaGoyrE=";
      };
      dependencies = with packages;
      with buildPackages;
      [mdurl];
      doCheck = false;
    };
    sniffio = buildPythonPackage {
      pname = "sniffio";
      version = "1.3.1";
      format="wheel";
      src = fetchurl {
        url="https://files.pythonhosted.org/packages/e9/44/75a9c9421471a6c4805dbf2356f7c181a29c1879239abab1ea2cc8f38b40/sniffio-1.3.1-py3-none-any.whl";
        hash="sha256-L22kGNHx4P3dhER49BaA55TmBRkVeRoDT/ZeXxAFJaI=";
      };
      doCheck = false;
    };
    idna = buildPythonPackage {
      pname = "idna";
      version = "3.7";
      format="wheel";
      src = fetchurl {
        url="https://files.pythonhosted.org/packages/e5/3e/741d8c82801c347547f8a2a06aa57dbb1992be9e948df2ea0eda2c8b79e8/idna-3.7-py3-none-any.whl";
        hash="sha256-gv7h/Hit1DSS06GJi/ptipBMyX2EJ/aD7Y55jQd2GqA=";
      };
      doCheck = false;
    };
    certifi = buildPythonPackage {
      pname = "certifi";
      version = "2024.7.4";
      format="wheel";
      src = fetchurl {
        url="https://files.pythonhosted.org/packages/1c/d5/c84e1a17bf61d4df64ca866a1c9a913874b4e9bdc131ec689a0ad013fb36/certifi-2024.7.4-py3-none-any.whl";
        hash="sha256-wZjiGxKJwquF7k5nu0tO8+rQiSBZkBqNW2IvJKEQHpA=";
      };
      doCheck = false;
    };
    anyio = buildPythonPackage {
      pname = "anyio";
      version = "4.4.0";
      format="wheel";
      src = fetchurl {
        url="https://files.pythonhosted.org/packages/7b/a2/10639a79341f6c019dedc95bd48a4928eed9f1d1197f4c04f546fc7ae0ff/anyio-4.4.0-py3-none-any.whl";
        hash="sha256-wbLY9GqKgSUTAS4RB8sOaMFxWaellCCABaV9x3bhvcc=";
      };
      dependencies = with packages;
      with buildPackages;
      [idna sniffio exceptiongroup typing-extensions];
      doCheck = false;
    };
    tomli = buildPythonPackage {
      pname = "tomli";
      version = "2.0.1";
      format="wheel";
      src = fetchurl {
        url="https://files.pythonhosted.org/packages/97/75/10a9ebee3fd790d20926a90a2547f0bf78f371b2f13aa822c759680ca7b9/tomli-2.0.1-py3-none-any.whl";
        hash="sha256-k53j56YWGvDIh++Rt9QaU+fFocqXYyX0KctG6pvDDsw=";
      };
      doCheck = false;
    };
    distro = buildPythonPackage {
      pname = "distro";
      version = "1.9.0";
      format="wheel";
      src = fetchurl {
        url="https://files.pythonhosted.org/packages/12/b3/231ffd4ab1fc9d679809f356cebee130ac7daa00d6d6f3206dd4fd137e9e/distro-1.9.0-py3-none-any.whl";
        hash="sha256-e//ZJdZRaPhQJ9jamva92rZYE1uEBnCiI1ibwMjvArI=";
      };
      doCheck = false;
    };
    httpx = buildPythonPackage {
      pname = "httpx";
      version = "0.27.0";
      format="wheel";
      src = fetchurl {
        url="https://files.pythonhosted.org/packages/41/7b/ddacf6dcebb42466abd03f368782142baa82e08fc0c1f8eaa05b4bae87d5/httpx-0.27.0-py3-none-any.whl";
        hash="sha256-cdVGUWLBNoG/8BrVmyzGjdg46h8Q5RV0usJxA/AMkaU=";
      };
      dependencies = with packages;
      with buildPackages;
      [anyio certifi httpcore idna sniffio];
      doCheck = false;
    };
    setuptools-scm = buildPythonPackage {
      pname = "setuptools-scm";
      version = "8.1.0";
      format="wheel";
      src = fetchurl {
        url="https://files.pythonhosted.org/packages/a0/b9/1906bfeb30f2fc13bb39bf7ddb8749784c05faadbd18a21cf141ba37bff2/setuptools_scm-8.1.0-py3-none-any.whl";
        hash="sha256-iXoyJqb9Sm6y8Gh0XklzMmGiH3Cxuyj84DOf65eNmvM=";
      };
      dependencies = with packages;
      with buildPackages;
      [packaging setuptools tomli];
      doCheck = false;
    };
    meson-python = buildPythonPackage {
      pname = "meson-python";
      version = "0.16.0";
      format="wheel";
      src = fetchurl {
        url="https://files.pythonhosted.org/packages/91/c0/104cb6244c83fe6bc3886f144cc433db0c0c78efac5dc00e409a5a08c87d/meson_python-0.16.0-py3-none-any.whl";
        hash="sha256-hC3J9dwp5V/Haf8bb+MoQS/myHAiD8MhBgodLTleaeg=";
      };
      dependencies = with packages;
      with buildPackages;
      [meson packaging pyproject-metadata tomli];
      doCheck = false;
    };
    scikit-build = buildPythonPackage {
      pname = "scikit-build";
      version = "0.18.0";
      format="wheel";
      src = fetchurl {
        url="https://files.pythonhosted.org/packages/24/43/a0b5837cf30db1561a04187edd262bdefaffcb61222cb441eadef35f9103/scikit_build-0.18.0-py3-none-any.whl";
        hash="sha256-6hcfVSnm4LW2Zhk0M4Ma9hoo1+35c7M4hOyMeCoV7jg=";
      };
      dependencies = with packages;
      with buildPackages;
      [distro packaging setuptools tomli wheel];
      doCheck = false;
    };
    packaging = buildPythonPackage {
      pname = "packaging";
      version = "24.1";
      format="wheel";
      src = fetchurl {
        url="https://files.pythonhosted.org/packages/08/aa/cc0199a5f0ad350994d660967a8efb233fe0416e4639146c089643407ce6/packaging-24.1-py3-none-any.whl";
        hash="sha256-W48iF9vb0vfzhMQcYoVE5tUvLQ9TxtDD6mGqXR1/8SQ=";
      };
      doCheck = false;
    };
    resolvelib = buildPythonPackage {
      pname = "resolvelib";
      version = "1.0.1";
      format="wheel";
      src = fetchurl {
        url="https://files.pythonhosted.org/packages/d2/fc/e9ccf0521607bcd244aa0b3fbd574f71b65e9ce6a112c83af988bbbe2e23/resolvelib-1.0.1-py2.py3-none-any.whl";
        hash="sha256-0tpF0ajf7oG91ZFkd4PjQO87yxBLVMOD9w1CLvXMfb8=";
      };
      doCheck = false;
    };
    rich = buildPythonPackage {
      pname = "rich";
      version = "13.7.1";
      format="wheel";
      src = fetchurl {
        url="https://files.pythonhosted.org/packages/87/67/a37f6214d0e9fe57f6ae54b2956d550ca8365857f42a1ce0392bb21d9410/rich-13.7.1-py3-none-any.whl";
        hash="sha256-TtuuMU9Z60gvVOnjC/ANMzUKqpT0v81OnjEQ5k0NciI=";
      };
      dependencies = with packages;
      with buildPackages;
      [markdown-it-py pygments];
      doCheck = false;
    };
    pybind11 = buildPythonPackage {
      pname = "pybind11";
      version = "2.13.1";
      format="wheel";
      src = fetchurl {
        url="https://files.pythonhosted.org/packages/84/fb/1a249de406daf2b4ebd2d714b739e8519034617daec085e3833c1a3ed57c/pybind11-2.13.1-py3-none-any.whl";
        hash="sha256-l4gVNqvgzUJgqczFv20c8xEzGPCK8f64LUuflek/CqQ=";
      };
      doCheck = false;
    };
    unearth = buildPythonPackage {
      pname = "unearth";
      version = "0.16.1";
      format="wheel";
      src = fetchurl {
        url="https://files.pythonhosted.org/packages/f3/08/ad4427cf0d0e19053d7e0b3405f2e6dcb697fb9bff61335a2024729402e2/unearth-0.16.1-py3-none-any.whl";
        hash="sha256-WlmKwaPxhRRPrcneR/EEO/+AXDYRj/xA+B75j/Iujjc=";
      };
      dependencies = with packages;
      with buildPackages;
      [packaging httpx];
      doCheck = false;
    };
    nixpy = buildPythonPackage {
      pname = "nixpy";
      version = "0.1.0";
      format="pyproject";
      src = ./.;
      build-system = with packages;
      with buildPackages;
      [setuptools];
      dependencies = with packages;
      with buildPackages;
      [unearth setuptools pybind11 rich resolvelib packaging requests pip scikit-build meson-python setuptools-scm];
      doCheck = false;
    };
  };
  buildPackages = rec {
  };
}
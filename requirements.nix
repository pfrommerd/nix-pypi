{buildPythonPackage, fetchurl, nixpkgs, python, nixpy-custom ? {}}: rec {
  packages = rec {
    nixpy = buildPythonPackage {
      pname = "nixpy";
      version = "0.1.0";
      format="pyproject";
      src = ./.;
      build-system = with packages;
      [setuptools];
      dependencies = with packages;
      [unearth rich resolvelib packaging requests build];
      doCheck=false;
    } ;
    rich = buildPythonPackage {
      pname = "rich";
      version = "13.7.1";
      format="wheel";
      src = fetchurl {
        url="https://files.pythonhosted.org/packages/87/67/a37f6214d0e9fe57f6ae54b2956d550ca8365857f42a1ce0392bb21d9410/rich-13.7.1-py3-none-any.whl";
        hash="sha256-TtuuMU9Z60gvVOnjC/ANMzUKqpT0v81OnjEQ5k0NciI=";
      };
      dependencies = with packages;
      [markdown-it-py pygments];
      doCheck=false;
    } ;
    resolvelib = buildPythonPackage {
      pname = "resolvelib";
      version = "1.0.1";
      format="wheel";
      src = fetchurl {
        url="https://files.pythonhosted.org/packages/d2/fc/e9ccf0521607bcd244aa0b3fbd574f71b65e9ce6a112c83af988bbbe2e23/resolvelib-1.0.1-py2.py3-none-any.whl";
        hash="sha256-0tpF0ajf7oG91ZFkd4PjQO87yxBLVMOD9w1CLvXMfb8=";
      };
      doCheck=false;
    } ;
    packaging = buildPythonPackage {
      pname = "packaging";
      version = "24.1";
      format="wheel";
      src = fetchurl {
        url="https://files.pythonhosted.org/packages/08/aa/cc0199a5f0ad350994d660967a8efb233fe0416e4639146c089643407ce6/packaging-24.1-py3-none-any.whl";
        hash="sha256-W48iF9vb0vfzhMQcYoVE5tUvLQ9TxtDD6mGqXR1/8SQ=";
      };
      doCheck=false;
    } ;
    build = buildPythonPackage {
      pname = "build";
      version = "1.2.1";
      format="wheel";
      src = fetchurl {
        url="https://files.pythonhosted.org/packages/e2/03/f3c8ba0a6b6e30d7d18c40faab90807c9bb5e9a1e3b2fe2008af624a9c97/build-1.2.1-py3-none-any.whl";
        hash="sha256-deEPdnpDPZqG5Q2D9BjoPvwY7ekj7l/335O2ywMGxdQ=";
      };
      dependencies = with packages;
      [packaging pyproject-hooks];
      doCheck=false;
    } ;
    pyproject-hooks = buildPythonPackage {
      pname = "pyproject-hooks";
      version = "1.1.0";
      format="wheel";
      src = fetchurl {
        url="https://files.pythonhosted.org/packages/ae/f3/431b9d5fe7d14af7a32340792ef43b8a714e7726f1d7b69cc4e8e7a3f1d7/pyproject_hooks-1.1.0-py3-none-any.whl";
        hash="sha256-fO7v6a7GOhBkwY2Tm9w63y2KoZiKUQr+wVFRV4sjKqI=";
      };
      doCheck=false;
    } ;
    unearth = buildPythonPackage {
      pname = "unearth";
      version = "0.17.0";
      format="wheel";
      src = fetchurl {
        url="https://files.pythonhosted.org/packages/03/c5/6c168746280d035e0eb511e20ee8256f11353bc3521ba92d36b27e347a71/unearth-0.17.0-py3-none-any.whl";
        hash="sha256-gcLx+tW7AGU3HfIhk0w8riLcdSbJYG7IP7NAXDrP1eY=";
      };
      dependencies = with packages;
      [packaging httpx];
      doCheck=false;
    } ;
    httpx = buildPythonPackage {
      pname = "httpx";
      version = "0.27.0";
      format="wheel";
      src = fetchurl {
        url="https://files.pythonhosted.org/packages/41/7b/ddacf6dcebb42466abd03f368782142baa82e08fc0c1f8eaa05b4bae87d5/httpx-0.27.0-py3-none-any.whl";
        hash="sha256-cdVGUWLBNoG/8BrVmyzGjdg46h8Q5RV0usJxA/AMkaU=";
      };
      dependencies = with packages;
      [anyio certifi httpcore idna sniffio];
      doCheck=false;
    } ;
    anyio = buildPythonPackage {
      pname = "anyio";
      version = "4.4.0";
      format="wheel";
      src = fetchurl {
        url="https://files.pythonhosted.org/packages/7b/a2/10639a79341f6c019dedc95bd48a4928eed9f1d1197f4c04f546fc7ae0ff/anyio-4.4.0-py3-none-any.whl";
        hash="sha256-wbLY9GqKgSUTAS4RB8sOaMFxWaellCCABaV9x3bhvcc=";
      };
      dependencies = with packages;
      [idna sniffio];
      doCheck=false;
    } ;
    certifi = buildPythonPackage {
      pname = "certifi";
      version = "2024.7.4";
      format="wheel";
      src = fetchurl {
        url="https://files.pythonhosted.org/packages/1c/d5/c84e1a17bf61d4df64ca866a1c9a913874b4e9bdc131ec689a0ad013fb36/certifi-2024.7.4-py3-none-any.whl";
        hash="sha256-wZjiGxKJwquF7k5nu0tO8+rQiSBZkBqNW2IvJKEQHpA=";
      };
      doCheck=false;
    } ;
    idna = buildPythonPackage {
      pname = "idna";
      version = "3.7";
      format="wheel";
      src = fetchurl {
        url="https://files.pythonhosted.org/packages/e5/3e/741d8c82801c347547f8a2a06aa57dbb1992be9e948df2ea0eda2c8b79e8/idna-3.7-py3-none-any.whl";
        hash="sha256-gv7h/Hit1DSS06GJi/ptipBMyX2EJ/aD7Y55jQd2GqA=";
      };
      doCheck=false;
    } ;
    sniffio = buildPythonPackage {
      pname = "sniffio";
      version = "1.3.1";
      format="wheel";
      src = fetchurl {
        url="https://files.pythonhosted.org/packages/e9/44/75a9c9421471a6c4805dbf2356f7c181a29c1879239abab1ea2cc8f38b40/sniffio-1.3.1-py3-none-any.whl";
        hash="sha256-L22kGNHx4P3dhER49BaA55TmBRkVeRoDT/ZeXxAFJaI=";
      };
      doCheck=false;
    } ;
    markdown-it-py = buildPythonPackage {
      pname = "markdown-it-py";
      version = "3.0.0";
      format="wheel";
      src = fetchurl {
        url="https://files.pythonhosted.org/packages/42/d7/1ec15b46af6af88f19b8e5ffea08fa375d433c998b8a7639e76935c14f1f/markdown_it_py-3.0.0-py3-none-any.whl";
        hash="sha256-NVIWhFxgvZYjLNjYxA6Pl2XMhvRogOQ6j9ItwaGoyrE=";
      };
      dependencies = with packages;
      [mdurl];
      doCheck=false;
    } ;
    mdurl = buildPythonPackage {
      pname = "mdurl";
      version = "0.1.2";
      format="wheel";
      src = fetchurl {
        url="https://files.pythonhosted.org/packages/b3/38/89ba8ad64ae25be8de66a6d463314cf1eb366222074cfda9ee839c56a4b4/mdurl-0.1.2-py3-none-any.whl";
        hash="sha256-hACKQeUWFaSfyZZhkf+RUJ48QLk5F25kP9UKXCGWuPg=";
      };
      doCheck=false;
    } ;
    requests = buildPythonPackage {
      pname = "requests";
      version = "2.32.3";
      format="wheel";
      src = fetchurl {
        url="https://files.pythonhosted.org/packages/f9/9b/335f9764261e915ed497fcdeb11df5dfd6f7bf257d4a6a2a686d80da4d54/requests-2.32.3-py3-none-any.whl";
        hash="sha256-cHYc/gPHc86yKqL2cbR1eXYUUXXN/KA4wCZU0GHW3MY=";
      };
      dependencies = with packages;
      [certifi charset-normalizer idna urllib3];
      doCheck=false;
    } ;
    httpcore = buildPythonPackage {
      pname = "httpcore";
      version = "1.0.5";
      format="wheel";
      src = fetchurl {
        url="https://files.pythonhosted.org/packages/78/d4/e5d7e4f2174f8a4d63c8897d79eb8fe2503f7ecc03282fee1fa2719c2704/httpcore-1.0.5-py3-none-any.whl";
        hash="sha256-Qh8YusJIsl0xDzys0ZjVW45hJcEHeXtgn/m3prp5kbU=";
      };
      dependencies = with packages;
      [certifi h11];
      doCheck=false;
    } ;
    h11 = buildPythonPackage {
      pname = "h11";
      version = "0.14.0";
      format="wheel";
      src = fetchurl {
        url="https://files.pythonhosted.org/packages/95/04/ff642e65ad6b90db43e668d70ffb6736436c7ce41fcc549f4e9472234127/h11-0.14.0-py3-none-any.whl";
        hash="sha256-4/5KxLhRxGjMg2PVANtSwurQNgIHIwJKEJ03NG76p2E=";
      };
      doCheck=false;
    } ;
    pygments = buildPythonPackage {
      pname = "pygments";
      version = "2.18.0";
      format="wheel";
      src = fetchurl {
        url="https://files.pythonhosted.org/packages/f7/3f/01c8b82017c199075f8f788d0d906b9ffbbc5a47dc9918a945e13d5a2bda/pygments-2.18.0-py3-none-any.whl";
        hash="sha256-uOasoFI/Ordv7lF5nEiOOHgqwG6vz5XnuoMphcjnsTo=";
      };
      doCheck=false;
    } ;
    charset-normalizer = buildPythonPackage {
      pname = "charset-normalizer";
      version = "3.3.2";
      format="wheel";
      src = fetchurl {
        url="https://files.pythonhosted.org/packages/28/76/e6222113b83e3622caa4bb41032d0b1bf785250607392e1b778aca0b8a7d/charset_normalizer-3.3.2-py3-none-any.whl";
        hash="sha256-Pk0fZYcyLSeIg2qZxpBi+7CRMx7JQOAtEtF5wdU+Jfw=";
      };
      doCheck=false;
    } ;
    urllib3 = buildPythonPackage {
      pname = "urllib3";
      version = "2.2.2";
      format="wheel";
      src = fetchurl {
        url="https://files.pythonhosted.org/packages/ca/1c/89ffc63a9605b583d5df2be791a27bc1a42b7c32bab68d3c8f2f73a98cd4/urllib3-2.2.2-py3-none-any.whl";
        hash="sha256-pEiy9k1oYVVGgDfhrOny0hmXduF/CkZhBIDTEfc+NHI=";
      };
      doCheck=false;
    } ;
    setuptools = buildPythonPackage {
      pname = "setuptools";
      version = "72.2.0";
      format="wheel";
      src = fetchurl {
        url="https://files.pythonhosted.org/packages/6e/ec/06715d912351edc453e37f93f3fc80dcffd5ca0e70386c87529aca296f05/setuptools-72.2.0-py3-none-any.whl";
        hash="sha256-8R3ZS3uuOhVqlewVHyTkY3+0+hnIeOTRkb+4stgnKMQ=";
      };
      doCheck=false;
    } ;
  };
  envs = {
    x86_64-linux = with packages;
    {
      certifi = certifi;
      packaging = packaging;
      anyio = anyio;
      charset-normalizer = charset-normalizer;
      mdurl = mdurl;
      requests = requests;
      markdown-it-py = markdown-it-py;
      urllib3 = urllib3;
      unearth = unearth;
      idna = idna;
      h11 = h11;
      pyproject-hooks = pyproject-hooks;
      rich = rich;
      nixpy = nixpy;
      build = build;
      sniffio = sniffio;
      httpcore = httpcore;
      resolvelib = resolvelib;
      pygments = pygments;
      httpx = httpx;
    };
    powerpc64le-linux = with packages;
    {
      pygments = pygments;
      urllib3 = urllib3;
      packaging = packaging;
      pyproject-hooks = pyproject-hooks;
      markdown-it-py = markdown-it-py;
      httpcore = httpcore;
      nixpy = nixpy;
      httpx = httpx;
      anyio = anyio;
      charset-normalizer = charset-normalizer;
      idna = idna;
      requests = requests;
      sniffio = sniffio;
      h11 = h11;
      unearth = unearth;
      mdurl = mdurl;
      certifi = certifi;
      rich = rich;
      build = build;
      resolvelib = resolvelib;
    };
    aarch64-darwin = with packages;
    {
      rich = rich;
      requests = requests;
      build = build;
      httpcore = httpcore;
      pyproject-hooks = pyproject-hooks;
      packaging = packaging;
      httpx = httpx;
      charset-normalizer = charset-normalizer;
      resolvelib = resolvelib;
      sniffio = sniffio;
      anyio = anyio;
      markdown-it-py = markdown-it-py;
      certifi = certifi;
      pygments = pygments;
      nixpy = nixpy;
      h11 = h11;
      unearth = unearth;
      idna = idna;
      urllib3 = urllib3;
      mdurl = mdurl;
    };
  };
  env = envs.${
    nixpkgs.system
  };
}
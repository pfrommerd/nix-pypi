{buildPythonPackage, fetchurl}: rec {
  packages = rec {
    urllib3 = buildPythonPackage {
      pname = "urllib3";
      version = "2.2.2";
      format="pyproject";
      src = fetchurl {
        url="https://files.pythonhosted.org/packages/43/6d/fa469ae21497ddc8bc93e5877702dca7cb8f911e337aca7452b5724f1bb6/urllib3-2.2.2.tar.gz";
        hash="sha256-3VBUhVSaelUoM9peYGNjnQ0XfATyO8OGTkHl3F9hIWg=";
      };
      doCheck = false;
      build-system = with packages;
      with buildPackages;
      [hatchling_1_25_0 trove-classifiers_2024_7_2 packaging pluggy_1_5_0 pathspec_0_12_1];
    };
    charset-normalizer = buildPythonPackage {
      pname = "charset-normalizer";
      version = "3.3.2";
      src = fetchurl {
        url="https://files.pythonhosted.org/packages/63/09/c1bc53dab74b1816a00d8d030de5bf98f724c52c1635e07681d312f20be8/charset-normalizer-3.3.2.tar.gz";
        hash="sha256-8ww8szskRUqC+uyvAbGcGFYrHolVj7bFbeTZEYoDL9U=";
      };
      doCheck = false;
      build-system = with packages;
      with buildPackages;
      [setuptools];
    };
    setuptools = buildPythonPackage {
      pname = "setuptools";
      version = "71.1.0";
      format="pyproject";
      src = fetchurl {
        url="https://files.pythonhosted.org/packages/32/c0/5b8013b5a812701c72e3b1e2b378edaa6514d06bee6704a5ab0d7fa52931/setuptools-71.1.0.tar.gz";
        hash="sha256-Ay1C7p+1NuMwh/tmysX4QOuTke0FY3s/KnanyPtHeTY=";
      };
      doCheck = false;
      build-system = with packages;
      with buildPackages;
      [];
    };
    idna = buildPythonPackage {
      pname = "idna";
      version = "3.7";
      format="pyproject";
      src = fetchurl {
        url="https://files.pythonhosted.org/packages/21/ed/f86a79a07470cb07819390452f178b3bef1d375f2ec021ecfc709fc7cf07/idna-3.7.tar.gz";
        hash="sha256-Ao/zqt8GCcH9J42OowiSmUEqeoub0AXdCLn4KFvLXPw=";
      };
      doCheck = false;
      build-system = with packages;
      with buildPackages;
      [flit-core_3_9_0];
    };
    h11 = buildPythonPackage {
      pname = "h11";
      version = "0.14.0";
      src = fetchurl {
        url="https://files.pythonhosted.org/packages/f5/38/3af3d3633a34a3316095b39c8e8fb4853a28a536e55d347bd8d8e9a14b03/h11-0.14.0.tar.gz";
        hash="sha256-jxn7vpnnJCD/NcALJ6NMuZN+kCqLgQ4siDAMbwo7aZ0=";
      };
      doCheck = false;
      build-system = with packages;
      with buildPackages;
      [setuptools];
    };
    httpcore = buildPythonPackage {
      pname = "httpcore";
      version = "1.0.5";
      format="pyproject";
      src = fetchurl {
        url="https://files.pythonhosted.org/packages/17/b0/5e8b8674f8d203335a62fdfcfa0d11ebe09e23613c3391033cbba35f7926/httpcore-1.0.5.tar.gz";
        hash="sha256-NKOOL5KRRn7jtE6J3VJhU3DhUpVLohchN4qHspYPemE=";
      };
      doCheck = false;
      build-system = with packages;
      with buildPackages;
      [certifi hatch-fancy-pypi-readme_24_1_0 hatchling_1_25_0 trove-classifiers_2024_7_2 h11 packaging pluggy_1_5_0 pathspec_0_12_1];
    };
    requests = buildPythonPackage {
      pname = "requests";
      version = "2.32.3";
      src = fetchurl {
        url="https://files.pythonhosted.org/packages/63/70/2bf7780ad2d390a8d301ad0b550f1581eadbd9a20f896afe06353c2a2913/requests-2.32.3.tar.gz";
        hash="sha256-VTZUF3NOsYJVWQqf+euX6eHaho1MzWQCOZ6vaK8gp2A=";
      };
      doCheck = false;
      build-system = with packages;
      with buildPackages;
      [setuptools idna charset-normalizer certifi urllib3];
    };
    sniffio = buildPythonPackage {
      pname = "sniffio";
      version = "1.3.1";
      format="pyproject";
      src = fetchurl {
        url="https://files.pythonhosted.org/packages/a2/87/a6771e1546d97e7e041b6ae58d80074f81b7d5121207425c964ddf5cfdbd/sniffio-1.3.1.tar.gz";
        hash="sha256-9DJO3GcKD0l1CoG4lfNcOtuEPMpG8FMPefwbq7I3idw=";
      };
      doCheck = false;
      build-system = with packages;
      with buildPackages;
      [setuptools-scm packaging setuptools];
    };
    pip = buildPythonPackage {
      pname = "pip";
      version = "24.1.2";
      format="pyproject";
      src = fetchurl {
        url="https://files.pythonhosted.org/packages/12/3d/d899257cace386bebb7bdf8a872d5fe3b935cc6381c3ddb76d3e5d99890d/pip-24.1.2.tar.gz";
        hash="sha256-5UWKC4nydV4O6MDHdhP+UnPgXzN5B4dNZPExcaiYp/8=";
      };
      doCheck = false;
      build-system = with packages;
      with buildPackages;
      [wheel_0_43_0 setuptools];
    };
    mdurl = buildPythonPackage {
      pname = "mdurl";
      version = "0.1.2";
      format="pyproject";
      src = fetchurl {
        url="https://files.pythonhosted.org/packages/d6/54/cfe61301667036ec958cb99bd3efefba235e65cdeb9c84d24a8293ba1d90/mdurl-0.1.2.tar.gz";
        hash="sha256-u0E9KfXuo48x3UdU3XN31EZRFvsgdYX5e/klWIaHwbo=";
      };
      doCheck = false;
      build-system = with packages;
      with buildPackages;
      [flit-core_3_9_0];
    };
    markdown-it-py = buildPythonPackage {
      pname = "markdown-it-py";
      version = "3.0.0";
      format="pyproject";
      src = fetchurl {
        url="https://files.pythonhosted.org/packages/38/71/3b932df36c1a044d397a1f92d1cf91ee0a503d91e470cbd670aa66b07ed0/markdown-it-py-3.0.0.tar.gz";
        hash="sha256-4/YKlPoGbcUux2Zh43yFHLIy2S+YhrFctWCqraLfj+s=";
      };
      doCheck = false;
      build-system = with packages;
      with buildPackages;
      [mdurl flit-core_3_9_0];
    };
    certifi = buildPythonPackage {
      pname = "certifi";
      version = "2024.7.4";
      src = fetchurl {
        url="https://files.pythonhosted.org/packages/c2/02/a95f2b11e207f68bc64d7aae9666fed2e2b3f307748d5123dffb72a1bbea/certifi-2024.7.4.tar.gz";
        hash="sha256-Wh52RbwOxhoJ4mw29hBt1M9Axts6H7Y1KwJE5/sFfHs=";
      };
      doCheck = false;
      build-system = with packages;
      with buildPackages;
      [setuptools];
    };
    anyio = buildPythonPackage {
      pname = "anyio";
      version = "4.4.0";
      format="pyproject";
      src = fetchurl {
        url="https://files.pythonhosted.org/packages/e6/e3/c4c8d473d6780ef1853d630d581f70d655b4f8d7553c6997958c283039a2/anyio-4.4.0.tar.gz";
        hash="sha256-Wq3Gobu3zbC+3jhsrF4pQPXi/zqiAnfpkc8CjgWFzpQ=";
      };
      doCheck = false;
      build-system = with packages;
      with buildPackages;
      [sniffio idna setuptools-scm packaging setuptools];
    };
    pygments = buildPythonPackage {
      pname = "pygments";
      version = "2.13.0";
      src = fetchurl {
        url="https://files.pythonhosted.org/packages/e0/ef/5905cd3642f2337d44143529c941cc3a02e5af16f0f65f81cbef7af452bb/Pygments-2.13.0.tar.gz";
        hash="sha256-VqhQiulfmOK5vfk6a+WuP32K+Fi0PgLFov8INya+QME=";
      };
      doCheck = false;
      build-system = with packages;
      with buildPackages;
      [setuptools];
    };
    httpx = buildPythonPackage {
      pname = "httpx";
      version = "0.27.0";
      format="pyproject";
      src = fetchurl {
        url="https://files.pythonhosted.org/packages/5c/2d/3da5bdf4408b8b2800061c339f240c1802f2e82d55e50bd39c5a881f47f0/httpx-0.27.0.tar.gz";
        hash="sha256-oMuIpG8y3IdOBO6VbkwnZKuiqiKPZQsGeIumvaKWKrU=";
      };
      doCheck = false;
      build-system = with packages;
      with buildPackages;
      [anyio certifi hatch-fancy-pypi-readme_24_1_0 hatchling_1_25_0 trove-classifiers_2024_7_2 packaging sniffio pluggy_1_5_0 httpcore h11 pathspec_0_12_1 idna];
    };
    setuptools-scm = buildPythonPackage {
      pname = "setuptools-scm";
      version = "8.1.0";
      format="pyproject";
      src = fetchurl {
        url="https://files.pythonhosted.org/packages/4f/a4/00a9ac1b555294710d4a68d2ce8dfdf39d72aa4d769a7395d05218d88a42/setuptools_scm-8.1.0.tar.gz";
        hash="sha256-Qt6htldxy6k7elFdZaZdgkblYHaKZrkQalksjn8myKc=";
      };
      doCheck = false;
      build-system = with packages;
      with buildPackages;
      [packaging setuptools];
    };
    packaging = buildPythonPackage {
      pname = "packaging";
      version = "24.1";
      format="pyproject";
      src = fetchurl {
        url="https://files.pythonhosted.org/packages/51/65/50db4dda066951078f0a96cf12f4b9ada6e4b811516bf0262c0f4f7064d4/packaging-24.1.tar.gz";
        hash="sha256-Am7XLI7T/M5b+JUFciWGmJJ/0dvaEKXpgc3wrDf08AI=";
      };
      doCheck = false;
      build-system = with packages;
      with buildPackages;
      [flit-core_3_9_0];
    };
    resolvelib = buildPythonPackage {
      pname = "resolvelib";
      version = "1.0.1";
      src = fetchurl {
        url="https://files.pythonhosted.org/packages/ce/10/f699366ce577423cbc3df3280063099054c23df70856465080798c6ebad6/resolvelib-1.0.1.tar.gz";
        hash="sha256-BM52y9Y/3tIHjOIkeF2m7NQrlWSxOQeT9k3ey+mXswk=";
      };
      doCheck = false;
      build-system = with packages;
      with buildPackages;
      [wheel_0_43_0 setuptools];
    };
    rich = buildPythonPackage {
      pname = "rich";
      version = "13.7.1";
      format="pyproject";
      src = fetchurl {
        url="https://files.pythonhosted.org/packages/b3/01/c954e134dc440ab5f96952fe52b4fdc64225530320a910473c1fe270d9aa/rich-13.7.1.tar.gz";
        hash="sha256-m+MIyx/i8fV9Z86Z6Vrzih4rxxrZgTsOJHz3/7zDpDI=";
      };
      doCheck = false;
      build-system = with packages;
      with buildPackages;
      [pygments markdown-it-py mdurl poetry-core_1_9_0];
    };
    pybind11 = buildPythonPackage {
      pname = "pybind11";
      version = "2.13.1";
      src = fetchurl {
        url="https://files.pythonhosted.org/packages/98/50/a8dc5a7b9fbb9a90dfc9003b3eecc046b9f64dc9b8d464119064c0344a83/pybind11-2.13.1.tar.gz";
        hash="sha256-Zb5JixysUWFhrdFQjmU3VnSRa+vyVw0FfcnDx7y7x7A=";
      };
      doCheck = false;
      build-system = with packages;
      with buildPackages;
      [wheel_0_43_0 setuptools];
    };
    unearth = buildPythonPackage {
      pname = "unearth";
      version = "0.16.1";
      format="pyproject";
      src = fetchurl {
        url="https://files.pythonhosted.org/packages/40/52/f20d419513a91ebbec226b3f7567bf5a662402c63cbd892a5fb1f5352a86/unearth-0.16.1.tar.gz";
        hash="sha256-mIpDQY+gt4rrYooV9qOwIVLBeH9j/m0lTH9OLM+NsKc=";
      };
      doCheck = false;
      build-system = with packages;
      with buildPackages;
      [httpx pdm-backend_2_3_3 anyio certifi sniffio httpcore h11 idna packaging];
    };
    nixpy = buildPythonPackage {
      pname = "nixpy";
      version = "0.1.0";
      format="pyproject";
      src = ./.;
      doCheck = false;
      build-system = with packages;
      with buildPackages;
      [unearth pybind11 rich resolvelib packaging setuptools-scm httpx pygments anyio certifi markdown-it-py mdurl pip sniffio requests httpcore h11 idna setuptools charset-normalizer urllib3];
    };
  };
  buildPackages = rec {
    pathspec_0_12_1 = buildPythonPackage {
      pname = "pathspec";
      version = "0.12.1";
      format="pyproject";
      src = fetchurl {
        url="https://files.pythonhosted.org/packages/ca/bc/f35b8446f4531a7cb215605d100cd88b7ac6f44ab3fc94870c120ab3adbf/pathspec-0.12.1.tar.gz";
        hash="sha256-pILVFQOhqzOxxnpsOBOiaVPb3HHDHayu+ag4xOKfVxI=";
      };
      doCheck = false;
      build-system = with packages;
      with buildPackages;
      [flit-core_3_9_0];
    };
    flit-core_3_9_0 = buildPythonPackage {
      pname = "flit-core";
      version = "3.9.0";
      format="pyproject";
      src = fetchurl {
        url="https://files.pythonhosted.org/packages/c4/e6/c1ac50fe3eebb38a155155711e6e864e254ce4b6e17fe2429b4c4d5b9e80/flit_core-3.9.0.tar.gz";
        hash="sha256-cq0mYXbEo/z6tfKTDXaJYFmFEkBXDOmphzO2WMt4bro=";
      };
      doCheck = false;
      build-system = with packages;
      with buildPackages;
      [];
    };
    pluggy_1_5_0 = buildPythonPackage {
      pname = "pluggy";
      version = "1.5.0";
      src = fetchurl {
        url="https://files.pythonhosted.org/packages/96/2d/02d4312c973c6050a18b314a5ad0b3210edb65a906f868e31c111dede4a6/pluggy-1.5.0.tar.gz";
        hash="sha256-LP+ojpT9yXjExXTxX55Zt/QgHUORlcNxXKniSG8dDPE=";
      };
      doCheck = false;
      build-system = with packages;
      with buildPackages;
      [setuptools-scm packaging setuptools];
    };
    trove-classifiers_2024_7_2 = buildPythonPackage {
      pname = "trove-classifiers";
      version = "2024.7.2";
      src = fetchurl {
        url="https://files.pythonhosted.org/packages/78/c9/83f915c3f6f94f4c862c7470284fd714f312cce8e3cf98361312bc02493d/trove_classifiers-2024.7.2.tar.gz";
        hash="sha256-gyjyrCzj/Xc8uzfHZaDteoP4ncVkx9RS8Dm2kknQrDU=";
      };
      doCheck = false;
      build-system = with packages;
      with buildPackages;
      [calver_2022_6_26 setuptools];
    };
    calver_2022_6_26 = buildPythonPackage {
      pname = "calver";
      version = "2022.6.26";
      src = fetchurl {
        url="https://files.pythonhosted.org/packages/b5/00/96cbed7c019c49ee04b8a08357a981983db7698ae6de402e57097cefc9ad/calver-2022.6.26.tar.gz";
        hash="sha256-4FSTo7F1F+8XSPvmENoR8QSF+qfEFrnTP9SlLXSJT4s=";
      };
      doCheck = false;
      build-system = with packages;
      with buildPackages;
      [setuptools];
    };
    hatchling_1_25_0 = buildPythonPackage {
      pname = "hatchling";
      version = "1.25.0";
      format="pyproject";
      src = fetchurl {
        url="https://files.pythonhosted.org/packages/a3/51/8a4a67a8174ce59cf49e816e38e9502900aea9b4af672d0127df8e10d3b0/hatchling-1.25.0.tar.gz";
        hash="sha256-cGRjGlEmELUiUKTT/xvYFVHW0UMcTre3LnNN9sdPQmI=";
      };
      doCheck = false;
      build-system = with packages;
      with buildPackages;
      [trove-classifiers_2024_7_2 packaging pluggy_1_5_0 pathspec_0_12_1];
    };
    hatch-fancy-pypi-readme_24_1_0 = buildPythonPackage {
      pname = "hatch-fancy-pypi-readme";
      version = "24.1.0";
      format="pyproject";
      src = fetchurl {
        url="https://files.pythonhosted.org/packages/b4/c2/c9094283a07dd96c5a8f7a5f1910259d40d2e29223b95dd875a6ca13b58f/hatch_fancy_pypi_readme-24.1.0.tar.gz";
        hash="sha256-RN0jnxp3m53PjryUAaYR/X9+PhRXjc8iwmXfr3wVFLg=";
      };
      doCheck = false;
      build-system = with packages;
      with buildPackages;
      [hatchling_1_25_0 trove-classifiers_2024_7_2 packaging pluggy_1_5_0 pathspec_0_12_1];
    };
    wheel_0_43_0 = buildPythonPackage {
      pname = "wheel";
      version = "0.43.0";
      format="pyproject";
      src = fetchurl {
        url="https://files.pythonhosted.org/packages/b8/d6/ac9cd92ea2ad502ff7c1ab683806a9deb34711a1e2bd8a59814e8fc27e69/wheel-0.43.0.tar.gz";
        hash="sha256-Rl75LGn6XF2i0c+KxAVZqMlAiGr874fc8UuUcIYvHYU=";
      };
      doCheck = false;
      build-system = with packages;
      with buildPackages;
      [flit-core_3_9_0];
    };
    poetry-core_1_9_0 = buildPythonPackage {
      pname = "poetry-core";
      version = "1.9.0";
      format="pyproject";
      src = fetchurl {
        url="https://files.pythonhosted.org/packages/f2/db/20a9f9cae3f3c213a8c406deb4395698459fd96962cea8f2ccb230b1943c/poetry_core-1.9.0.tar.gz";
        hash="sha256-+npAAeroqlcu6E81/rUQsyG9ZS5c+SkySdYoU+H5NaI=";
      };
      doCheck = false;
      build-system = with packages;
      with buildPackages;
      [];
    };
    pdm-backend_2_3_3 = buildPythonPackage {
      pname = "pdm-backend";
      version = "2.3.3";
      format="pyproject";
      src = fetchurl {
        url="https://files.pythonhosted.org/packages/75/2b/0be2d0f2eba3a4acb755fd2b0e442ef67770b2ef6c75fd646d49f20968fa/pdm_backend-2.3.3.tar.gz";
        hash="sha256-qGFvYo7IQ1PXoLqGsijc8BurXevJ5NGinlMRpSQl1ZQ=";
      };
      doCheck = false;
      build-system = with packages;
      with buildPackages;
      [];
    };
  };
  env = with packages;
  [urllib3 charset-normalizer setuptools idna h11 httpcore requests sniffio pip mdurl markdown-it-py certifi anyio pygments httpx setuptools-scm packaging resolvelib rich pybind11 unearth nixpy];
}
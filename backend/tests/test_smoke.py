def test_package_imports():
    import zilpzalp
    from importlib.metadata import version

    assert zilpzalp.__version__ == version("zilpzalp")

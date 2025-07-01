import pytest
import importlib

providers = {
    'doodstream': 'https://doodstream.com/e/18q92knltur6',
    'filemoon': 'https://filemoon.to/e/eawuwyrd40an',
    'loadx': 'https://loadx.ws/video/1acbf888c0941af3700e671d096ba635',
    'luluvdo': 'https://luluvdo.com/embed/g1gaitimtoc1',
    'speedfiles': 'https://speedfiles.net/4f8b2c8d4f3f',
    'streamtape': '',
    'vidmoly': 'https://vidmoly.to/embed-19xpz8qoujf9.html',
    'vidoza': 'https://vidoza.net/embed-k2wiaenfxn9j.html',
    'voe': 'https://voe.sx/e/ayginbzzb6bi'
}


@pytest.mark.parametrize("name,url", providers.items())
def test_get_direct_link(name, url):
    if not url:
        pytest.skip(f"No URL provided for {name}")

    func = getattr(
        importlib.import_module(f'aniworld.extractors.provider.{name}'),
        f'get_direct_link_from_{name}'
    )

    try:
        direct_link = func(url)
        assert direct_link is not None and isinstance(direct_link, str)
    except Exception as e:
        pytest.fail(f"{name}: Exception occurred - {e}")

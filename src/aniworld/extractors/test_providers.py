import importlib

providers = {
    'doodstream': 'https://doodstream.com/e/18q92knltur6',  # embeded broken?
    'filemoon': 'https://filemoon.to/e/eawuwyrd40an',  # embeded broken?
    'loadx': 'https://loadx.ws/video/7b7bd53ba5107cf5fb2c2a51dd887c95',
    'luluvdo': 'https://luluvdo.com/embed/g1gaitimtoc1',
    'speedfiles': 'https://speedfiles.net/4f8b2c8d4f3f',
    'streamtape': '',  # add link
    'vidmoly': 'https://vidmoly.to/embed-19xpz8qoujf9.html',
    'vidoza': 'https://vidoza.net/embed-k2wiaenfxn9j.html',
    'voe': 'https://voe.sx/e/ayginbzzb6bi'
}

for name, url in providers.items():
    func = getattr(
        importlib.import_module(f'aniworld.extractors.provider.{name}'),
        f'get_direct_link_from_{name}'
    )

    try:
        print('*' * 40)
        print(name.upper())
        direct_link = func(url)
        if direct_link:
            print(direct_link)
        else:
            print("None")
    except:
        print("None")
        continue

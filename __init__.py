def classFactory(iface):
    from .plugin import CoastalInundationPlugin
    return CoastalInundationPlugin(iface)

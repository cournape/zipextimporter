r"""zipextimporter - an importer which can import extension modules from zipfiles

This file and also memimporter.pyd is part of the py2exe package.

Overview
========

zipextimporter.py contains the ZipExtImporter class which allows to
load Python binary extension modules contained in a zip.archive,
without unpacking them to the file system.

Call the zipextimporter.install() function to install the import hook,
add a zip-file containing .pyd or .dll extension modules to sys.path,
and import them.

It uses the memimporter extension which uses code from Joachim
Bauch's MemoryModule library.  This library emulates the win32 api
function LoadLibrary.

Sample usage
============

You have to prepare a zip-archive 'lib.zip' containing
your Python's _socket.pyd for this example to work.

>>> import zipextimporter
>>> zipextimporter.install()
>>> import sys
>>> sys.path.insert(0, "lib.zip")
>>> import _socket
>>> print _socket
<module '_socket' from 'lib.zip\_socket.pyd'>
>>> _socket.__file__
'lib.zip\\_socket.pyd'
>>> _socket.__loader__
<ZipExtensionImporter object 'lib.zip'>
>>> # Reloading also works correctly:
>>> _socket is reload(_socket)
True
>>>

"""
import imp, sys
import zipimport
import memimporter

class ZipExtensionImporter(zipimport.zipimporter):
    _suffixes = [s[0] for s in imp.get_suffixes() if s[2] == imp.C_EXTENSION]

    def find_loader(self, fullname, path=None):
        loader = self.find_module(fullname, path)
        return (loader, [])

    def find_module(self, fullname, path=None):
        result = zipimport.zipimporter.find_module(self, fullname, path)
        if result:
            return result
        if fullname in ("pywintypes", "pythoncom"):
            fullname = fullname + "%d%d" % sys.version_info[:2]
            fullname = fullname.replace(".", "\\") + ".dll"
            if fullname in self._files:
                return self
        else:
            fullname = fullname.replace(".", "\\")
            for s in self._suffixes:
                if (fullname + s) in self._files:
                    return self
        return None

    def locate_dll_image(self, name):
        # A callback function formemimporter.import_module.  Tries to
        # locate additional dlls.  Returns the image as Python string,
        # or None if not found.
        if name in self._files:
            return self.get_data(name)
        return None

    def load_module(self, fullname):
        if fullname in sys.modules:
            mod = sys.modules[fullname]
            if memimporter.get_verbose_flag():
                sys.stderr.write("import %s # previously loaded from zipfile %s\n" % (fullname, self.archive))
            return mod
        memimporter.set_find_proc(self.locate_dll_image)
        try:
            return zipimport.zipimporter.load_module(self, fullname)
        except zipimport.ZipImportError:
            pass
         # name of initfunction
        if sys.version[0] > '3':
            initname = "init" + fullname.split(".")[-1]
        else:
            initname = "PyInit_" + fullname.split(".")[-1]
        filename = fullname.replace(".", "\\")
        if filename in ("pywintypes", "pythoncom"):
            filename = filename + "%d%d" % sys.version_info[:2]
            suffixes = ('.dll',)
        else:
            suffixes = self._suffixes
        for s in suffixes:
            path = filename + s
            if path in self._files:
                if memimporter.get_verbose_flag():
                    sys.stderr.write("# found %s in zipfile %s\n" % (path, self.archive))
                code = self.get_data(path)
                mod = memimporter.import_module(code, initname, fullname, path)
                mod.__file__ = "%s\\%s" % (self.archive, path)
                mod.__loader__ = self
                sys.modules[fullname] = mod
                if memimporter.get_verbose_flag():
                    sys.stderr.write("import %s # loaded from zipfile %s\n" % (fullname, mod.__file__))
                return mod
        raise zipimport.ZipImportError("can't find module %s" % fullname)

    def __repr__(self):
        return "<%s object %r>" % (self.__class__.__name__, self.archive)

def install():
    "Install the zipextimporter"
    sys.path_hooks.insert(0, ZipExtensionImporter)
    sys.path_importer_cache.clear()

##if __name__ == "__main__":
##    import doctest
##    doctest.testmod()

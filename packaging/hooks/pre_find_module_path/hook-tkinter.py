"""Mantém o Tkinter disponível no runtime Python portátil usado no build."""


def pre_find_module_path(_hook_api):
    # O runtime portátil possui Tcl/Tk, mas a sonda isolada do PyInstaller não
    # consegue inicializá-lo. Os dados e DLLs são incluídos pelo script de build.
    return None

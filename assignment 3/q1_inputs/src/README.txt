This synthetic source tree is for a bash/sed/awk assignment.

Task ideas:
1. Replace '#include <oldlib.h>' with '#include <newlib.h>'
   but ONLY in .c/.h files that contain a call to init_adapter().
2. Walk recursively through the tree.
3. Be careful: some files contain the old include but do not call init_adapter().
4. Some files call init_adapter() but do not include oldlib.h.
5. Several files also contain TEMPDEBUG markers.

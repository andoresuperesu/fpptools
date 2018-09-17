# FppTools

FppTools is a set of debugging tools geared towards the analysis and correction of str, blk and job files belonging to the implementation of the software [FP Pro](http://www.emmegisoft.com/en/product/fp-pro).

## How do I use this?

Usage is simple so far as the only command available is list_fittings. At the moment it *requires* 2 arguments:

* `--searchtype` is obligatory
* `--tofile y` or `--verbose y`

```cmd
C:\users\user>fpptools
Usage: fpptools [OPTIONS] COMMAND [ARGS]...

  Debugging and administration python package for Emmegisoft's FP Pro

Options:
  --help  Show this message and exit.

Commands:
  list_fittings  Generate a fitting list of str/blk/job(s)
```

## Reference

### Commands

#### list_fittings

This is the only active commands in this tool so far. It is designed to extract information about the fittings pressent in all str, blk or jobrecord files; or entire job folder.

Usage:
```cmd
c:\users\user>fpptools list_fittings --searchtype [searchtype] --tofile [y/n] --verbose [y/n]
```


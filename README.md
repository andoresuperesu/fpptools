# FppTools

FppTools is a set of debugging tools geared towards the analysis and correction of str, blk and job files belonging to the implementation of the software [FP Pro](http://www.emmegisoft.com/en/product/fp-pro).

## How do I use this?

Usage is simple so far as the only command available is list_fittings. It *requires* 2 arguments to direct its output:

* `--searchtype` is obligatory, either 
* `--tofile` 

```console
C:\users\user>fpptools
Usage: fpptools [OPTIONS] COMMAND [ARGS]...

  Debugging and administration python package for Emmegisoft's FP Pro

Options:
  --help  Show this message and exit.

Commands:
  list_fittings  Generate a fitting list of str/blk/job(s)
```
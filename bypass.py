import logging
import argparse
from os.path import isfile, isdir, splitext, join, exists, dirname
from os import walk, makedirs
from glob import glob
if __name__ == "__main__":
    logger = logging.getLogger(__name__)
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description="Club Penguin client tool")
    parser.add_argument("path", type=str, nargs="*", help="Path(s) to files or directories")
    arguments = parser.parse_args()

    logger.info("This program can overwrite files on the disk, make sure to make backups before" +
                " running this script or make sure the output flag is enabled!")
                
    for path in arguments.path:
        if isfile(path):
            logger.info("Found \"%s\"", path)
            paths = [path]
        elif isdir(path):
            paths = [y for x in walk(path) for y in glob(join(x[0], '*.js'))]
        for file in paths:
            logger.info("Found \"%s\"", file)
            filename, file_extension = splitext(file)
            if file_extension != ".js":
                logger.warning("\"%s\" is not an JS file! skipping...", path)
            logger.info("Opening \"%s\"", file)
            raw = open(file,'r')
            raw = raw.read()
            f = open(file,'w+')
            new = raw.replace('{data;}', '{return;}')
            f.write(new)
            f.close()
    logger.info("Finished. Goodbye!")
    

from __future__ import absolute_import, division, print_function
import os
import sys
import datetime
import traceback

dir_path = os.path.abspath(os.path.dirname(__file__))
root_path = os.path.join(dir_path, '..', '..', '..')
sys.path.insert(0, dir_path)
sys.path.insert(0, root_path)

class Benchmark(object):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def bench(self):
        raise NotImplementedError("You must implement the bench() method in a"
                                  "custom benchmark class.")

    def more_info(self):
        return {}

    def run(self):
        start = end = None

        print("-" * 70)
        print("Running %s..." % self.__class__.__name__)
        try:
            # Set up first.
            self.setUp()

            # Get time, then run benchmark.
            start = datetime.datetime.now()
            self.bench()
            end = datetime.datetime.now()

            self.tearDown()

        except Exception as e:
            print("")
            print("Caught exception!", file=sys.stderr)
            if start is not None:
                exc_time = (datetime.datetime.now() - start).seconds
                print("   Time before exception: %d seconds" % exc_time)

            print("-" * 70, file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
            print("-" * 70, file=sys.stderr)

        if start is not None and end is not None:
            time = (end - start)
            time_seconds = time.seconds + (time.microseconds / 1000000)

            print("")
            print("-" * 70)
            print("Benchmark %s:" % self.__class__.__name__)
            print("-" * 70)
            print("   Time Taken: %f seconds" % time_seconds)

            inf = self.more_info(time)
            for k, v in inf.items():
                print("   %s: %s" % (k, v))

            print("-" * 70)



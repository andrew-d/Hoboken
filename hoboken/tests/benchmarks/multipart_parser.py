#!/usr/bin/env python
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from bench import Benchmark
from hoboken.objects.mixins.request_body import MultipartParser


def sizeof_fmt(num):
    for x in ['bytes', 'KiB', 'MiB', 'GiB']:
        if num < 1024.0:
            return "%3.1f%s" % (num, x)
        num /= 1024.0
    return "%3.1f%s" % (num, 'TiB')


class MultipartParserBenchmark(Benchmark):
    def setUp(self):
        self.parser = MultipartParser(b'--boundary', {})

        # Write headers.
        before = b'----boundary\r\nContent-Disposition: form-data; name="file"; filename="test.txt"\r\nContent-Type: text/plain\r\n\r\n'
        self.parser.write(before)

        # Configure here.
        self.DATA_SIZE = 10 * 1024 * 1024
        self.ITERATIONS = 100
        self.total_size = self.DATA_SIZE * self.ITERATIONS

    def bench(self):
        # Create data and setup variables
        data = 'A' * self.DATA_SIZE

        # Write data.
        parser = self.parser
        for i in range(self.ITERATIONS):
            parser.write(data)
            sys.stdout.write('.')
            sys.stdout.flush()

    def tearDown(self):
        # Write trailer.
        after = b'\r\n----boundary--\r\n'
        self.parser.write(after)

    def more_info(self, time_taken):
        speed = self.total_size / time_taken.seconds

        return {
            "Total Bytes Written": self.total_size,
            "Total Data Written": sizeof_fmt(self.total_size),
            "Speed": sizeof_fmt(speed) + "/sec",
        }


if __name__ == "__main__":
    MultipartParserBenchmark().run()

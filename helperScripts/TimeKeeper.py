import time


class TimeKeeper:
    def __init__(self):
        pass

    
    def startPerfCounter(self):
        """Start an internal counter for evaluating performance. Stop with
        stopPerfCounter()"""
        self.perfCounter = [time.perf_counter(), 0]


    def returnPerfCounter(self):
        """Stop internal perf_counter and return elapsed time"""
        self.perfCounter[1] = time.perf_counter()

        return (self.perfCounter[1]-self.perfCounter[0])
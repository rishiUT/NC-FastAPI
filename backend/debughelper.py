import datetime

debug = True
debug_error = True
debug_timeline = True
no_val = "?:;!@"

class DebugPrinter:
    def __init__(self) -> None:
        timestamp = str(datetime.datetime.now())
        file_name = "logs/debug_log_" + timestamp + ".tsv"
        self.output_file = open(file_name, 'a')
        headers = "Timestamp\tloc\tUID\tMturkID\tMessage"
        print(headers, file=self.output_file)
        file_name = "timelines/timeline_" + timestamp + ".txt"
        self.output_file_timeline = open(file_name, 'a')

    def print(self, loc: str, message: str, uid=no_val, mturk_id=no_val):
        if debug:
            to_print = message

            if mturk_id != no_val:
                to_print = str(mturk_id) + "\t" + to_print
            else:
                to_print = "<no value>" + "\t" + to_print
                
            if uid != no_val:
                to_print = str(uid) + "\t" + to_print
            else:
                to_print = "<no value>" + "\t" + to_print

            to_print = str(loc) + "\t" + to_print
            to_print = str(datetime.datetime.now()) + "\t" + to_print

            print(to_print, flush=True)
            if self.output_file is not None:
                print(to_print, file=self.output_file, flush=True)
                
    def print_error(self, loc: str, message: str, uid=no_val, mturk_id=no_val):
        file_name = "logs/flag_error.txt"
        open(file_name, 'w')
        
        if debug_error:
            to_print = message

            if mturk_id != no_val:
                to_print = str(mturk_id) + "\t" + to_print
            else:
                to_print = "<no value>" + "\t" + to_print
                
            if uid != no_val:
                to_print = str(uid) + "\t" + to_print
            else:
                to_print = "<no value>" + "\t" + to_print

            to_print = str(loc) + "\t" + to_print
            to_print = str(datetime.datetime.now()) + "\t" + to_print

            print(to_print, flush=True)
            if self.output_file is not None:
                print(to_print, file=self.output_file, flush=True)
                                
    def print_user_friendly(self, message: str):
        if debug_timeline:
            to_print = message
            to_print = str(datetime.datetime.now()) + "\t" + to_print
            print(to_print, flush=True)

            if self.output_file_timeline is not None:
                print(to_print, file=self.output_file_timeline, flush=True)
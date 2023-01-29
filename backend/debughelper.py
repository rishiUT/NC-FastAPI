class DebugPrinter:
    def __init__(self) -> None:
        pass

    def set_output_file_name(self, output_file_name):
        self.output = output_file_name

    def set_output_file(self, output_file):
        self.output_file = output_file

    def print(self, to_print: str):
        print(to_print)
        if self.output_file is not None:
            print(to_print, file=self.output_file)
        elif self.output is not None:
            with open(self.output, 'a') as f:
                print(to_print, file=f)
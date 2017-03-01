import logging


class GeneratingGrammarTablesFilter(logging.Filter):

    def filter(self, record):
        if 'Generating grammar tables' in record.msg:
            return False
        return True

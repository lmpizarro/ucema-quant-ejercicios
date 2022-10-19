from tabulate import tabulate

class IRPrinter:
    """
    Class to print current implicit rates
    """
    EMPTY_ROW_STR = '*' * 12 + ' -> ' + '*' * 10

    def __init__(self, ir_expert):
        self._ir_expert = ir_expert

    def print_rates(self):
        #Get the implicit rates and sort them
        taker_rates = self._ir_expert.taker_rates()
        offered_rates = self._ir_expert.offered_rates()
        taker_rates_print = {maturity_tag: sorted(
            [(ticker, rate) for ticker, rate in values.items()], key=lambda x: x[1])
            for maturity_tag, values in taker_rates.items()}
        offered_rates_print = {maturity_tag: sorted(
            [(ticker, rate) for ticker, rate in values.items()], key=lambda x: x[1])
            for maturity_tag, values in offered_rates.items()}

        #Then fill the empty rows in maturities with few values
        maturity_tags = set(taker_rates.keys()).union(set(offered_rates.keys()))
        max_taker_entries = max(len(entries) for entries in taker_rates_print.values())
        max_offered_entries = max(len(entries) for entries in taker_rates_print.values())
        rates_to_print = {}
        for maturity_tag in maturity_tags:
            taker_values = taker_rates_print.get(maturity_tag, [self.EMPTY_ROW_STR] * max_taker_entries)
            rates_to_print[maturity_tag] = (
                    [self.EMPTY_ROW_STR] * (max_taker_entries - len(taker_values))
                    + [f'{value[0]:<12} -> {value[1]:10.6f}' for value in taker_values])
            offered_values = offered_rates_print.get(maturity_tag, [self.EMPTY_ROW_STR] * max_offered_entries)
            rates_to_print[maturity_tag] += ['+' * 26]
            rates_to_print[maturity_tag] += [f'{value[0]:<12} -> {value[1]:10.6f}' for value in offered_values] + \
                                            [self.EMPTY_ROW_STR] * (max_offered_entries - len(offered_values))
        table_str = ('Last Updated Rates:\n' +
                     tabulate(rates_to_print, headers='keys', stralign='center', tablefmt='psql'))
        print(table_str, flush=True)

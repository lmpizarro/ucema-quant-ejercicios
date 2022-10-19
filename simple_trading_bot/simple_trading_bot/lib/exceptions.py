class ExpiredInstrument(Exception):

    def __init__(self, instrument):
        msg = f'Instrument expired on {instrument.maturity_date()}'
        super().__init__(msg)
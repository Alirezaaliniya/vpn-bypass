import subprocess

from account_cleaner.processes import ClientProcess


def cp(out=""):
    return subprocess.CompletedProcess([], 0, stdout=out, stderr="")


def test_pids_parses_tasklist_csv():
    out = '"Windscribe.exe","1234","Console","1","50,000 K"\n"Windscribe.exe","99","Console","1","1 K"\n'
    c = ClientProcess(runner=lambda a: cp(out))
    assert c.pids() == [1234, 99]


def test_no_match_message():
    c = ClientProcess(runner=lambda a: cp("INFO: No tasks are running which match the specified criteria.\n"))
    assert c.pids() == [] and not c.is_running()


def test_other_process_not_matched():
    c = ClientProcess(runner=lambda a: cp('"WindscribeService.exe","5","Services","0","1 K"\n'))
    assert c.pids() == []


class Sim:
    """Simulates a process that dies on polite close or only on /F."""

    def __init__(self, dies_on):
        self.alive = True
        self.dies_on = dies_on
        self.calls = []

    def __call__(self, args):
        self.calls.append(args)
        if args[0] == "tasklist":
            return cp('"Windscribe.exe","7","Console","1","1 K"\n' if self.alive else "")
        if self.dies_on == "polite" and "/F" not in args:
            self.alive = False
        if self.dies_on == "force" and "/F" in args:
            self.alive = False
        return cp()


def fake_time():
    t = [0.0]
    return (lambda s: t.__setitem__(0, t[0] + s)), (lambda: t[0])


def test_polite_close_is_enough():
    sleep, clock = fake_time()
    sim = Sim("polite")
    assert ClientProcess(runner=sim, sleep=sleep, clock=clock).close()
    assert not any("/F" in c for c in sim.calls)


def test_escalates_to_force():
    sleep, clock = fake_time()
    sim = Sim("force")
    assert ClientProcess(runner=sim, sleep=sleep, clock=clock).close()
    assert any("/F" in c for c in sim.calls)


def test_gives_up_if_it_never_dies():
    sleep, clock = fake_time()
    assert not ClientProcess(runner=Sim("never"), sleep=sleep, clock=clock).close()

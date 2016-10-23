from itty import *
from tropo import Tropo, Result

c = "yes,no"


@post('/index.json')
def index(request):

    t = Tropo()

    t.say("Welcome to the Penguin Shelter Finder")
    t.on(event="finish", next="/finish")

    return t.RenderJson()


@post("/finish")
def finish(request):

    t = Tropo()
    t.ask(name="dob", timeout=10,
          say="Please say your date of birth")
    t.on(event="gotDOB", next="/gotDOB")
    return t.RenderJson()


@post("/gotDOB")
def gotdog(request):

    r = Result(request.body)
    t = Tropo()

    answer = r.getValue()

    t.on(event="finishDOB", next="/finishDOB")

    return t.RenderJson()


@post("/finishDOB")
def index(request):

    t = Tropo()
    t.ask(name="gender", timeout=10, say="Please provide your gender")
    t.on(event="gotGender", next="/gotGender")
    return t.RenderJson()


@post("/gotGender")
def index(request):

    t = Tropo()
    r = Result(request.body)

    answer = r.getValue()

    t.on(event="finishGender", next="/finishGender")

    return t.RenderJson()


@post("/finishGender")
def index(request):

    t = Tropo()
    t.ask(c, name="dependents", timeout=10, say="Do you have any children?")
    t.on(event="gotDepend", next="/gotDepend")

    return t.RenderJson()


@post("/gotDepend")
def index(request):
    t = Tropo()
    r = Result(request.body)

    answer = r.getValue()

    t.on(event="finishDepend", next="/finishDepend")

    return t.RenderJson()


@post("/finishDepend")
def index(request):
    t = Tropo()
    t.ask(c, name="veteran", timeout=10, say="Are you a veteran?")
    t.on(event="gotVeteran", next="/gotVeteran")

    return t.RenderJson()


@post("/gotVeteran")
def index(request):
    t = Tropo()
    r = Result(request.body)

    answer = r.getValue()

    t.on(event="finishVeteran", next="/finishVeteran")

    return t.RenderJson()


@post("/finishVeteran")
def index(request):
    t = Tropo()
    t.ask(c, timeout=10, name="disability",
          say="Do you have a physical disability?")
    t.on(event="gotDisable", next="/gotDisable")

    return t.RenderJson()


@post("/gotDisable")
def index(request):
    t = Tropo()
    r = Result(request.body)

    answer = r.getValue()

    t.on(event="finishDisable", next="/finishDisable")

    return t.RenderJson()


@post("/finishDisable")
def index(request):
    t = Tropo()
    t.ask(c, timeout=10, name="chronic",
          say="Do you have any chronic health conditions?")
    t.on(event="gotChronic", next="/gotChronic")

    return t.RenderJson()


@post("/gotDisable")
def index(request):
    t = Tropo()
    r = Result(request.body)

    answer = r.getValue()

    t.on(event="finishChronic", next="/finishChronic")

    return t.RenderJson()


@post("/finishChronic")
def index(request):
    t = Tropo()
    t.ask(c, timeout=10, name="mental",
          say="Do you have any mental health conditions?")
    t.on(event="gotMental", next="/gotMental")

    return t.RenderJson()


@post("/gotMental")
def index(request):
    t = Tropo()
    r = Result(request.body)

    answer = r.getValue()

    t.on(event="finishMental", next="/finishMental")

    return t.RenderJson()


@post("/finishMental")
def index(request):
    t = Tropo()
    t.ask(c, timeout=10, name="substance",
          say="Do you suffer from substance abuse?")
    t.on(event="gotSubstance", next="/gotSubstance")

    return t.RenderJson()


@post("/gotSubstance")
def index(request):
    t = Tropo()
    r = Result(request.body)

    answer = r.getValue()

    t.on(event="finishSubstance", next="/finishSubstance")
    t.RenderJson()


@post("/finishSubstance")
def index(request):
    t = Tropo()
    t.ask(c, timeout=10, name="domestic",
          say="Are you a victim of domestic abuse?")
    t.on(event="gotAbuse", next="/gotAbuse")

    return t.RenderJson()


@post("/gotAbuse")
def index(request):
    t = Tropo()
    r = Result(request.body)

    answer = r.getValue()

    t.on(event="finishAbuse", next="/finishAbuse")
    t.RenderJson()

run_itty(server='wsgiref', host='0.0.0.0', port=8888)

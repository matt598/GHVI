from tropo import Tropo, Result, Choices
from itty import post, run_itty
from redis import StrictRedis
from pyzipcode import ZipCodeDatabase
from datetime import datetime
import json
import os
import pymysql


def get_phone_info_from_payphone(number):
    with conn.cursor() as cur:
        cur.execute("""
            select
                phone.`id`,
                phone.`city`,
                phone.`state`,
                phone.`latitude`,
                phone.`longitude`
            from
                phone
            where
                phone.`number` = %s
        """, (number))

        return cur.fetchone()


def get_nearby_shelters_from_coords(latitude, longitude):
    with conn.cursor() as cur:
        cur.execute("""
            select
                shelter.`id`,
                shelter.`name`,
                shelter.`address`,
                shelter.`beds_available`,
                shelter.`beds_full`,
                shelter.`min_age`,
                shelter.`max_age`,
                shelter.`allow_male`,
                shelter.`allow_female`,
                shelter.`allow_trans`,
                shelter.`disability`,
                shelter.`dependent`,
                shelter.`abuse`,
                shelter.`veteran`,
                haversine(shelter.latitude, shelter.longitude, %s, %s) distance
            from
                shelter
            where
                shelter.`beds_available` <> shelter.`beds_full`
            order by
                distance asc
            limit
                50
        """, (latitude, longitude))

        return cur.fetchall()


def set_with_expiry(sess, key, value, ttl=120):
    k = '%s:%s' % (sess, key)
    r.set(k, value)
    r.expire(k, ttl)


def get(sess, key):
    return r.get('%s:%s' % (sess, key))


@post('/index.json')
def index(request):
    t = Tropo()

    t.say('Welcome to the shelter finder')

    s = json.loads(request.body)
    callerID = s['session']['from']['id']
    phone = get_phone_info_from_payphone(callerID)

    data = json.loads(request.body)

    if phone:
        set_with_expiry(data['session']['id'], 'coords', json.dumps({
            'lat': phone[3],
            'lng': phone[4]
        }))

        phone = get_phone_info_from_payphone(callerID)
        t.say('I see you are calling from {city}, {state}.'.format(
            city=phone[1], state=phone[2]))
        t.on(event='continue', next='/dob.json')
    else:
        c = Choices('[5 DIGITS]', mode='dtmf')
        t.ask(c, say='Please enter your ZIP code')
        t.on(event='continue', next='/zip.json')

    return t.RenderJson()


@post('/zip.json')
def zip(request):
    t = Tropo()
    r = Result(request.body)

    try:
        i = r.getInterpretation()
    except:
        t.say('Unknown ZIP code!')
        return t.RenderJson()

    zcdb = ZipCodeDatabase()
    place = zcdb[i]

    set_with_expiry(r._sessionId, 'coords', json.dumps({
        'lat': place.latitude,
        'lng': place.longitude,
    }))

    t.on(event='continue', next='/dob.json')

    return t.RenderJson()


@post('/dob.json')
def dob(request):
    t = Tropo()

    year = Choices('[4 DIGITS]', mode='dtmf')
    t.ask(year, say='What is your four digit birth year?', name='year')

    month = Choices('[1-2 DIGITS]', mode='dtmf')
    t.ask(month, say='What is your birth month as a number?', name='month')

    day = Choices('[1-2 DIGITS]', mode='dtmf')
    t.ask(day, say='What is your birth day?', name='day')

    t.on(event='continue', next='/limiters.json')

    return t.RenderJson()


@post('/limiters.json')
def limiters(request):
    t = Tropo()
    r = json.loads(request.body)['result']

    birthday = {}

    for action in r['actions']:
        birthday[action['name']] = int(action['interpretation'])

    try:
        dt = datetime(birthday['year'], birthday['month'], birthday['day'])
    except:
        t.say('Invalid date')
        t.on(event='continue', next='/dob.json')
        return t.RenderJson()

    set_with_expiry(r['sessionId'], 'birthday', json.dumps(birthday))

    def veteran_val():
        n = datetime.now()
        return n.year - dt.year >= 18

    yesno = Choices('1,2,yes,no', mode='any')
    opts = [{
        'name': 'gender',
        'msg': 'What is your gender? 1 for male, 2 for female, 3 transgender male to female, 4 transgender female to male',
        'choice': Choices('1,2,3,4')
    }, {
        'msg': 'Enter 1 for yes or 2 for no'
    }, {
        'name': 'dependent',
        'msg': 'Do you have any children?',
        'choice': yesno,
    }, {
        'name': 'veteran',
        'msg': 'Are you a veteran?',
        'ok': veteran_val,
        'choice': yesno,
    }, {
        'name': 'disability',
        'msg': 'Do you have any disabilities?',
        'choice': yesno,
    }, {
        'name': 'abuse',
        'msg': 'Are you the victim of abuse?',
        'choice': yesno,
    }]

    for opt in opts:
        if 'ok' not in opt or opt['ok']():
            if 'choice' in opt:
                t.ask(opt['choice'], say=opt['msg'], name=opt['name'])
            else:
                t.say(opt['msg'])

    t.on(event='continue', next='/places.json')

    return t.RenderJson()


@post('/places.json')
def places(request):
    t = Tropo()
    r = Result(request.body)

    sess = r._sessionId
    d = json.loads(get(sess, 'coords'))

    shelters = get_nearby_shelters_from_coords(d['lat'], d['lng'])

    r = json.loads(request.body)['result']

    answers = {}
    birthday = json.loads(get(sess, 'birthday'))

    dt = datetime(birthday['year'], birthday['month'], birthday['day'])
    age = datetime.now().year - dt.year

    for action in r['actions']:
        answers[action['name']] = int(action['interpretation'])

    print(answers)
    print(birthday)

    def isyes(ans):
        return ans == '1' or ans == 'yes'

    def istrans(ans):
        return ans == '2' or ans == '3'

    def ismale(ans):
        return ans == '1'

    def isfemale(ans):
        return ans == '0'

    has_said = 0

    for shelter in shelters:
        if shelter[3] == shelter[4]:  # beds are full
            continue

        if shelter[13] and (not 'veteran' in answers or not isyes(answers['veteran'])):
            continue

        if shelter[12] and not isyes(answers['abuse']):
            continue

        if shelter[11] and (not isyes(answers['dependent']) and age > 18):
            continue

        if shelter[10] and not isyes(answers['disability']):
            continue

        if not shelter[9] and istrans(answers['gender']):
            continue

        if not shelter[8] and not isfemale(answers['gender']):
            continue

        if not shelter[7] and not ismale(answers['gender']):
            continue

        if shelter[5] and age < shelter[5] and not isyes(answers['dependent']):
            continue

        if shelter[6] and age > shelter[6] and not isyes(answers['dependent']):
            continue

        has_said += 1
        t.say(shelter[1])

        if has_said > 5:
            break

    return t.RenderJson()


if __name__ == '__main__':
    r = StrictRedis()
    conn = pymysql.connect(host=os.environ['MYSQL_HOST'],
                           port=int(os.environ['MYSQL_PORT']),
                           user=os.environ['MYSQL_USER'],
                           passwd=os.environ['MYSQL_PASS'],
                           db=os.environ['MYSQL_DB'])

    run_itty(host='0.0.0.0', port=8080)

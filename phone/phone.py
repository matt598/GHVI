from tropo import Tropo, Result, Choices
from itty import post, run_itty
from redis import StrictRedis
from pyzipcode import ZipCodeDatabase
from datetime import datetime
import json
import os
import pymysql
import requests


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
            'lat': float(phone[3]),
            'lng': float(phone[4]),
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


def get_better_yearish(dt):
    return dt.year + (dt.month / 12) + (dt.day / 30)


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
        return get_better_yearish(n) - get_better_yearish(dt) >= 18

    yesno = Choices('1,2,yes,no', mode='any')
    opts = [{
        'name': 'gender',
        'msg': 'What is your gender? 1 for female, 2 for male, 3 transgender male to female, 4 transgender female to male',
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
    age = get_better_yearish(datetime.now()) - get_better_yearish(dt)

    for action in r['actions']:
        answers[action['name']] = action['interpretation']

    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO client
                (dob, gender, dependents, veteran, domestic, disability)
                VALUES (%s, %s, %s, %s, %s, %s)
        """,
                    ('%d-%d-%d' % (dt.year, dt.month, dt.day),
                     int(answers['gender']) - 1,
                     answers['dependent'] == '1',
                     answers['veteran'] == '1',
                     answers['abuse'] == '1',
                     answers['disability'] == '1',
                     )
                    )
        conn.commit()

        set_with_expiry(sess, 'client', cur.lastrowid)

    def isyes(ans):
        return ans == '1' or ans == 'yes'

    def istrans(ans):
        return ans == '3' or ans == '4'

    def ismale(ans):
        return ans == '2'

    def isfemale(ans):
        return ans == '1'

    has_said = 0

    spoken_shelters = []
    saved_shelters = {}

    for shelter in shelters:
        if shelter[3] == shelter[4]:  # beds are full
            continue

        if shelter[13] == '1' and (not 'veteran' in answers or not isyes(answers['veteran'])):
            continue

        if shelter[12] == '1' and not isyes(answers['abuse']):
            continue

        if shelter[11] == '1' and (not isyes(answers['dependent']) and age > 18):
            continue

        if shelter[10] == '1' and not isyes(answers['disability']):
            continue

        if shelter[9] == '0' and istrans(answers['gender']):
            continue

        if shelter[8] == '0' and not isfemale(answers['gender']):
            continue

        if shelter[7] == '0' and not ismale(answers['gender']):
            continue

        if shelter[5] == '1' and age < shelter[5] and not isyes(answers['dependent']):
            continue

        if shelter[6] == '1' and age > shelter[6] and not isyes(answers['dependent']):
            continue

        has_said += 1
        spoken_shelters.append('%d. %s. %s' %
                               (has_said, shelter[1], shelter[2]))
        saved_shelters[has_said] = shelter[0]

        if has_said > 5:
            break

    set_with_expiry(sess, 'saved', json.dumps(saved_shelters))

    t.say('You may enter a number to notify the location that you are on the way. ')

    t.ask(Choices('1,2,3,4,5'), say='. '.join(
        spoken_shelters), timeout=120, mode='dtmf')

    t.on(event='continue', next='/info.json')

    return t.RenderJson()


@post('/info.json')
def info(request):
    t = Tropo()
    r = Result(request.body)

    sess = r._sessionId
    d = json.loads(get(sess, 'saved'))
    u = get(sess, 'client')

    i = r.getInterpretation()

    with conn.cursor() as cur:
        cur.execute("""
            SELECT name, email FROM shelter WHERE id = %s
        """, (d[i]))

        shelter = cur.fetchone()

        cur.execute("""SELECT dob, gender FROM client WHERE id = %s""", (u))

        user = cur.fetchone()

    print('User %s going to location %s' % (u, shelter[0]))

    gender = [
        'female',
        'male',
        'transgender male to female',
        'transgender female to male',
    ][user[1]]

    request_url = 'https://api.mailgun.net/v2/{domain}/messages'.format(domain=os.environ['DOMAIN'])
    r = requests.post(request_url, auth=('api', os.environ['MAILGUN']), data={
        'from': 'no-reply@ghc.li',
        'to': shelter[1],
        'subject': 'Incoming person',
        'text': """There is an incoming {gender} person

        Birth date: {year}-{month}-{day}

        System ID: {id}
        """.format(id=u, year=user[0].year, month=user[0].month, day=user[0].day, gender=gender)
    })

    t.say('We have notified %s that you are on the way.' % (shelter[0]))

    return t.RenderJson()


if __name__ == '__main__':
    r = StrictRedis()
    conn = pymysql.connect(host=os.environ['MYSQL_HOST'],
                           port=int(os.environ['MYSQL_PORT']),
                           user=os.environ['MYSQL_USER'],
                           passwd=os.environ['MYSQL_PASS'],
                           db=os.environ['MYSQL_DB'])

    run_itty(host='0.0.0.0', port=8080)

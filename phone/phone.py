from tropo import Tropo, Session, Result, Choices
from itty import post, run_itty
from redis import StrictRedis
from pyzipcode import ZipCodeDatabase
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
                haversine(shelter.latitude, shelter.longitude, %s, %s) distance
            from
                shelter
            order by
                distance asc
            limit
                5
        """, (latitude, longitude))

        return cur.fetchall()


def set_with_expiry(sess, key, value, ttl=120):
    r.set('%s:%s' % (sess, key), value)
    r.expire(key, ttl)


def get(sess, key):
    return r.get('%s:%s' % (sess, key))


@post('/index.json')
def index(request):
    t = Tropo()

    t.say('Welcome to the shelter finder')

    s = json.loads(request.body)
    callerID = s['from']['id']
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

    year = Choices('[4 DIGITS]', mode='dtmf', name='year')
    t.ask(year, say='What is your four digit birth year?')

    month = Choices('[1-2 DIGITS]', mode='dtmf', name='month')
    t.ask(month, say='What is your birth month as a number?')

    day = Choices('[1-2 DIGITS]', mode='dtmf', name='day')
    t.ask(day, say='What is your birth day?')

    t.on(event='continue', next='/limiters.json')

    return t.RenderJson()


@post('/limiters.json')
def limiters(request):
    t = Tropo()
    r = Result(request.body)

    try:
        i = r.getInterpretation()
    except:
        t.say('Invalid input.')

        return t.RenderJson()

    print(i)


@post('/places.json')
def places(request):
    t = Tropo()
    r = Result(request.body)

    d = json.loads(get(r._sessionId, 'coords'))

    shelters = get_nearby_shelters_from_coords(d['lat'], d['lng'])

    for shelter in shelters:
        t.say(shelter[1])

    return t.RenderJson()


if __name__ == '__main__':
    r = StrictRedis()
    conn = pymysql.connect(host=os.environ['MYSQL_HOST'],
                           port=int(os.environ['MYSQL_PORT']),
                           user=os.environ['MYSQL_USER'],
                           passwd=os.environ['MYSQL_PASS'],
                           db=os.environ['MYSQL_DB'])

    run_itty(host='0.0.0.0', port=8080)

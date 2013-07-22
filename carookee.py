#!/usr/bin/env python
"""
MODULE:    carookee

AUTHOR(S): Holger Mueller <zarath@gmx.de>

PURPOSE:   Script to dump the textual content of a carookee forum

COPYRIGHT: (C) 2013 Holger Mueller

           This Program is free software under the Apache
           License Version 2.0.
"""
from requests import Session
import lxml.html
import re


def _get_pagecount(html):
    """look if there is more then on page of topics or posts"""
    nums = 0
    base = ""
    for ele in html.iter('a'):
        href = ele.get('href', '')
        if href.endswith('#bot'):
            base, nums = href[:-4].split('?p=')
            base += "?p="
            break
    return base, int(nums)

def get_topics(html):
    return [(e.get('href'), e.text)
            for e in html.iter('a')
            if e.get('class', '') == 'topictitle']

class Carookee(Session):
    """requests Session class extended by login and dump
       methods for carookee's forum website"""

    DOMAIN = "http://www.carookee.net"

    RXP_DATE = re.compile(r'''
        ^[^:]+:\s+
        ([0-3][0-9]\.[01][0-9]\.\d{2},\s+[0-2][0-9]:[0-5][0-9])
        \s+[^:]+:\s+(\S.*)
        ''', re.X | re.U)

    def __init__(self, forum, *args, **kwargs):
        Session.__init__(self, *args, **kwargs)
        self.forum = forum


    def get_html(self, url):
        """get the url and parse it with lxml.html
           returns: lxml.html Elementtree"""
        res = self.get(url)
        html = lxml.html.fromstring(res.content)
        html.make_links_absolute(self.DOMAIN)
        return html


    def login(self, username, password):
        html = self.get_html ("%s/forum/%s/login" % (self.DOMAIN, self.forum))
        vals = {}
        for elem in html.iter('input'):
            vals[elem.name] = elem.value
        vals['username'] = username
        vals['password'] = password
        action = html.forms[0].action
        res = self.post(action, vals)
        return res.ok


    def list_subforums(self):
        html = self.get_html("%s/forum/%s" % (self.DOMAIN, self.forum))
        subf = []
        for elem in html.iter('a'):
            if elem.get('class', '') == 'forumlink':
                subf.append((elem.get('href'), elem.text))
        return subf


    def list_topics(self, sflink):


        html = self.get_html(sflink)
        topics = []
        topics.extend(get_topics(html))

        # look for more then on page of topics
        base, nums = _get_pagecount(html)
        for i in range (2, nums + 1):
            html = self.get_html("%s%i" %(base, i))
            topics.extend(get_topics(html))
        return topics


    def get_topic(self, tplink):
        html = self.get_html(tplink)
        pages = []
        posts = []
        pages.append(html)

        base, nums = _get_pagecount(html)
        for i in range (2, nums + 1):
            pages.append(self.get_html("%s%i" %(base, i)))

        for page in pages:
            # find table with the content
            for row in page.findall(".//table[@class='forumline']./tr"):
                try:
                    author = row.find(".//span[@class='name']").text_content()
                except:
                    author = ""

                try:
                    detail = row.find(".//span[@class='postdetails'][1]"
                            ).text_content()
                    date, subject = self.RXP_DATE.search(detail).groups()

                except:
                    date = ""
                    subject = ""

                try:
                    content = row.find(".//span[@class='postbody']"
                            ).text_content()
                except:
                    content = ""

                if content:
                    posts.append({
                        'author': author,
                        'date': date,
                        'subject': subject,
                        'content': content,
                        })
        return posts


if __name__ == '__main__':
    import sys
    import json

    forum, username, password = sys.argv[1:]

    c = Carookee(forum)
    c.login(username, password)

    sforums = c.list_subforums()

    print "["

    for link, fname in sforums[:2]:
        topics = c.list_topics(link)
        for link, tname in topics:
            t = c.get_topic(link)
            json.dump({
                'Forum': fname,
                'Topic': tname,
                'Thread': t,
                }, sys.stdout, indent=4)
            print ","
    print "{}]"

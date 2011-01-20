#!/usr/bin/env python
"""This module provides a tool for fetching UIUC course sections information

Example:
>>> fetcher = UIUCCourseFetcher(2011, 'Spring')
>>> fetcher.fetch('CS',493)
{'CS': {493: {31260: {'section': 'CS', 'days': 'W', 
'location': 'room 1105, Siebel Center for Comp Sci', 
'time': '04:00 PM - 04:50 PM', 'instructor': 'Woodley, M', 
'type': 'lecture- discussion'}}}}
>>> fetcher.fetch() # Get all course info
""" 

import sys
import os
import datetime
import urllib2
import HTMLParser
import re
import pprint

class UIUCSubjectListParser(HTMLParser.HTMLParser):
    """a parser for http://courses.illinois.edu/cis/2011/spring/schedule/index.html"""
    
    def __init__(self):
        HTMLParser.HTMLParser.__init__(self)
        self.subject_list = []
        self.ready = False
        
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag.lower() == 'div' and attrs.get('class') == 'ws-course-number':
            self.ready = True
        else:
            self.ready = False
            
    def handle_data(self, data):
        if self.ready == True:
            self.subject_list.append(data)
            
    def get_result(self):
        return self.subject_list


class UIUCCourseListParser(HTMLParser.HTMLParser):
    """a parser for http://courses.illinois.edu/cis/2011/spring/schedule/{subject}/index.html""" 
    
    def __init__(self):
        HTMLParser.HTMLParser.__init__(self)
        self.course_no = []
        self.ready = False
        
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag.lower() == 'div' and attrs.get('class') == 'ws-course-number':
            self.ready = True
        else:
            self.ready = False
            
    def handle_data(self, data):
        if self.ready:
            self.course_no.append(data.split(' ')[1])

    def get_result(self):
        return self.course_no
    
class UIUCSectionListParser(HTMLParser.HTMLParser):
    """a parser for http://courses.illinois.edu/cis/2011/spring/schedule/{subject}/{course_no}.html"""
    
    def __init__(self):
        HTMLParser.HTMLParser.__init__(self)
        self.sections = {}
        self.current_crn = None
        self.property_to_write = None
        self.headers = ['ws-crn', 'ws-type', 'ws-section', 'ws-time', 
        'ws-days', 'ws-location', 'ws-instructor']
        self.re_cleaner = re.compile('\s+')
        
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag.lower() == 'br' and self.property_to_write == 'ws-location':
            return
        if tag.lower() == 'td' and (attrs.get('headers') in self.headers and 
                                    attrs.get('class').strip()) == 'ws-row':
            self.property_to_write = attrs.get('headers')
        else:
            self.property_to_write = None
            
    def handle_data(self, data):
        if self.property_to_write == 'ws-crn':
            try:
                self.current_crn = int(data)
            except:
                self.current_crn = None
            else:
                self.sections[self.current_crn] = {}
        elif self.current_crn != None and self.property_to_write != None:
            data = self.re_cleaner.sub(' ', data.strip())
            if self.property_to_write == 'ws-crn':
                self.current_crn = int(data)
                self.sections[self.current_crn] = {}                
            else:
                current_section = self.sections[self.current_crn]
                if current_section.get(self.property_to_write[3:]) == None:
                    current_section[self.property_to_write[3:]] = data
                else:
                    current_section[self.property_to_write[3:]] += ', ' + data
                
    def get_result(self):
        return self.sections

        
class UIUCCourseFetcher():
    """Fetch data from http://course.illinois.edu for a certain term."""
    
    def __init__(self, year=None, term=None):
        """Initialize with a certain term.
        
        Arguments:
        year -- Year to request (default: current year)
        semester -- Semester to request (default: current semester)
        
        """
        
        year = datetime.date.today().year if year is None else year
        term = term.lower() if term is not None else term
            
        if term == None or (term != 'spring' or 
                            term != 'fall' or term !='summer'):
            if datetime.date.today().month < 5:
                term = 'spring'
            elif datetime.date.today().month < 8:
                term = 'summer'
            else:
                term = 'fall'
        
        site_root = 'http://courses.illinois.edu/cis/'
                
        self.urls = {
            'root'     : site_root + str(year) + '/' + term + '/schedule/',
            'portal' : site_root + str(year) + '/' + term + '/schedule/index.html',
        }
        
        self.flush()
    
    def __parse_url(self, parser=None, url=None):
        if parser == None or url == None:
            return
            
        f = urllib2.urlopen(url)
        hp = parser()
        for line in f:
            hp.feed(line)
        r = hp.get_result()
        
        f.close()
        hp.close()
        
        return r
        
    def fetch_subject_list(self):
        if self.subject_list == None:
            self.subject_list = self.__parse_url(UIUCSubjectListParser, 
                                                 self.urls['portal'])
        return self.subject_list
    
    def fetch_course_list(self, subject):
        if not self.course_list.get(subject):
            subj_url = self.urls['root'] + subject.upper() + '/'
            self.course_list[subject] = self.__parse_url(UIUCCourseListParser, 
                                                         subj_url)
        return self.course_list[subject]
    
    def fetch_section_list(self, subject, course_no):
        if not self.section_list.get(subject):
            self.section_list[subject] = {}
        if not self.section_list[subject].get(course_no):
            course_url = self.urls['root'] + subject.upper() + '/' + str(course_no) + '.html'
            self.section_list[subject][course_no] = self.__parse_url(UIUCSectionListParser, course_url)
        return self.section_list[subject][course_no]

    def fetch_all(self):
        return self.fetch()
    
    def fetch(self, subject=None, course_no=None):
        """Get section info for all courses, or all courses in a subject, or a specified course.
        
        Arguments:
        subject -- The subject to look up. Can be a string for a single subject or a tuple for multiple subjects.
        course_no -- The course number to look up. Must be specified with a single subject string, otherwise will be ignored.
        
        Returns:
        A dictionary for sections
        """
        if type(subject) == type(str()):
            if course_no is None:
                subject_list = [subject]
            else:
                return { subject: 
                            { course_no: 
                                self.fetch_section_list(subject, course_no)
                            }
                        }
        elif type(subject) == type(list()):
            subject_list = subject
        else:
            subject_list = self.fetch_subject_list()
         
        course_list = {}
        section_list = {}
             
        for subject in subject_list:
            course_list[subject] = self.fetch_course_list(subject)
            section_list[subject] = {}

            for course in course_list[subject]:
                section_list[subject][course] = self.fetch_section_list(subject, course)        
                
        return section_list
            
    def flush(self):
        self.subject_list = None
        self.course_list = {}
        self.section_list = {}
            
def main():
    f = UIUCCourseFetcher()
    print f.fetch('art', 140)

if __name__ == '__main__':
    main()


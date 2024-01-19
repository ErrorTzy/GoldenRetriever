import re
import asyncio
from yarl import URL

def strip_html_text(html_title: str):
        if not html_title:
            return None
        return re.sub(r'^[\n\t\s]+|[\n\t\s]+$', '', html_title)


def get_clean_string_from_URL(node_URL: URL):
    node_url_string = node_URL.scheme + "://" +\
        node_URL.host + \
        node_URL.path + \
        node_URL.query_string

    return node_url_string


def get_sub_host(root_url_object: URL):
        sub_host = ".".join(root_url_object.host.split('.')[1:])
        assert len(sub_host)
        return sub_host

def a_element_href_to_URL(url_obj: URL, a_element_href: str):
    try:
        a_element_raw_URL = URL(a_element_href)
        
        # contents like <a href='/a.html'>
        if a_element_href.startswith('/'):
            a_element_href_URL = URL(
                url_obj.scheme + "://" + url_obj.host + a_element_href)
            return a_element_href_URL, False
        # contents like <a href='a.html'>, <a href='#'>
        elif a_element_raw_URL.scheme == '':
            a_element_href_URL = URL(url_obj.scheme + "://" + url_obj.host +
                                    url_obj.path[:url_obj.path.rfind('/')+1] + a_element_href)
            return a_element_href_URL, False
        # contents like <a href='http://example.com/a.html'>
        elif "http" in a_element_raw_URL.scheme:
            return URL(a_element_href), True
        else:
             return None, None
    except ValueError:
        return None, None

def empty_queue(q):
    """
    DESCRIPTION:
        empty all tasks in a queue
        
    INPUT: 
        q: the asyncio queue needed to be emptied

    OUTPUT: 
        none
    """

    while not q.empty():
        # Depending on your program, you may want to
        # catch QueueEmpty
        try:
            q.get_nowait()
            q.task_done()
        except asyncio.QueueEmpty:
            break
import asyncio
import aiohttp
from lxml import html
from fake_headers import Headers
from anytree import Node
from yarl import URL
# from web_scanner_settings import *
from web_scanner_utils import a_element_href_to_URL, empty_queue, strip_html_text, get_clean_string_from_URL, get_sub_host

def filter(function) -> None:
    def checker(node: Node, *paras):
        try:
            function(node, *paras)
        except AssertionError:
            node.parent = None
            assert False
    return checker

class WebScanner:
    _node_queue = None
    _branch_queue = None
    _header_queue = None
    _session = None
    _remaining_node = None

    # settings field
    link_limit = None
    max_retry = None
    connection_time_out = None
    proxy_handler = lambda self: None
    on_node_ready_filter = lambda self, node: None
    on_URL_ready_filter = lambda self, node, URL: None
    on_dom_tree_ready_filter = lambda self, node, tree: None
    on_response_headers_ready_filter = lambda self, node, response: None

    # data field
    scanned_url_record = {}
    worker_size = None
    root_node = None

    def __init__(self):
        pass


    def _main_workers_working(self):
        return self.worker_size


    async def _header_worker(self):

        header_generator = Headers(headers=True)
        while self._main_workers_working():
            await self._header_queue.put(header_generator.generate())

        print("headers generation complete")


    async def _tree_grower(self):

        """
        This worker will:
            1. try to fetch the page. If 
                a. it does not respond with a content type, or
                b. text/html is not in its content type,
                c. it content pass match the regex rool from CONTENT_FILTER,
            then it will detach itself from its parent and put itself to the queue 
            in order to notify the result work this link is irrelavant.

            2. Then it will search all the a elements in a page and check them.
            It will create a node list containing all the nodes that passes through
            the domain filter, then put it to the branch list.
        """

        while True:
            url_node = await self._node_queue.get()
            if not url_node:
                break
            url_obj = url_node.name['URL']

            tree = None
            try:
                self.on_node_ready_filter(url_node)
                self.on_URL_ready_filter(url_node, url_obj)
                tree = await self._get_dom_tree(url_node, url_obj)
            except AssertionError:
                await self._branch_queue.put(url_obj)
                continue
            except UnicodeDecodeError:
                url_node.parent = None
                await self._branch_queue.put(url_obj)
                continue

            if not tree:
                pass
            a_elements = tree.xpath('//a')
            await self._process_a_elements(url_node, url_obj, a_elements)
            

        self.worker_size -= 1
        print(f"workers remaining {self.worker_size}")
        if not self.worker_size:
            print("all workers complete")
            empty_queue(self._header_queue)


    async def _process_a_elements(self, url_node, url_obj, a_elements):
        # hrefs_set here is to avoid repetition. key: url value: if it passed
        checked_hrefs = set()
        node_list = []
        for a_element in a_elements:
            try:
                a_element_href = a_element.get('href')
                assert a_element_href

                a_element_href_URL, need_check_host = a_element_href_to_URL(
                        url_obj, a_element_href)
                assert a_element_href_URL

                # If is already checked and but did not pass, then jump to the next one
                a_element_href_url_string = str(a_element_href_URL)
                assert a_element_href_url_string not in checked_hrefs

                # separate domain from url and check if it passess the domain filter
                if need_check_host:
                    self.on_URL_ready_filter(url_node, a_element_href_URL)

                new_a_element_node = Node({
                        'URL': a_element_href_URL,
                        'title': strip_html_text(a_element.text_content())
                    }, parent=url_node)

                self.on_node_ready_filter(new_a_element_node)

                checked_hrefs.add(a_element_href_url_string)
                node_list.append(
                        new_a_element_node)
            except AssertionError:
                pass

        await self._branch_queue.put(node_list)

    async def _get_dom_tree(self, url_node: Node, url_obj: URL):

        rand_headers = await self._header_queue.get()
        # add referer
        referrer_URL = None
        if url_node.parent:
            referrer_node = url_node.parent
            referrer_URL = referrer_node.name['URL']
            rand_headers["Referer"] = str(referrer_URL)
        
        retry = 0
        while True:
            assert retry < self.max_retry
            try:
                async with self._session.get(url_obj, headers=rand_headers,
                                    proxy=self.proxy_handler(),
                                    timeout=self.connection_time_out,
                                    allow_redirects=True) as response:
                    
                    self.on_response_headers_ready_filter(url_node, response)
                    response_url_string = str(response.url)
                    if response_url_string != str(url_obj):
                        redirect_node = Node(url_node.name.copy(), parent=url_node.parent)
                        redirect_node.name['URL'] = response.url
                        self.on_URL_ready_filter(redirect_node, response.url)
                        # Here, on_node_ready_filter is not called because this filter is not supposed to check URL,
                        # while the only thing changed here is URL. Therefore, only on_URL_ready_filter is called.
                        await self._branch_queue.put([redirect_node])
                        assert False

                    html_content = await response.text(encoding="utf8")
                    assert html_content

                    tree = html.fromstring(html_content)
                    self.on_dom_tree_ready_filter(url_node, tree) # if it passes content filter
                    return tree

            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                print(f"retrying {url_obj}\n\t({type(e).__name__}:{e})")
                retry += 1
                await asyncio.sleep(1)


    async def _result_worker(self):
        """
        if it receives a node list, check if it is repetitive and 
        put the non repetitive ones to the queue.

        if it receives a string, then mark it as irrelavent
        """

        while True:
            node_list = await self._branch_queue.get()

            if type(node_list) is URL:
                clean_url = get_clean_string_from_URL(node_list)
                if clean_url in self.scanned_url_record and self.scanned_url_record[clean_url]:
                    self.scanned_url_record[node_list] = False
                    self._remaining_node -= 1
                    print(f"remaining_node:{self._remaining_node}")

            else:
                new_brench_length = -1
                for node in node_list:
                    node_URL = node.name['URL']
                    node_url_string = get_clean_string_from_URL(node_URL)

                    if node_url_string not in self.scanned_url_record:
                        self.scanned_url_record[node_url_string] = True
                        await self._node_queue.put(node)
                        new_brench_length += 1
                    else:
                        node.parent = None

                self._remaining_node += new_brench_length
                print(f"remaining_node:{self._remaining_node}")

            if not self._remaining_node:
                for _ in range(self.worker_size):
                    await self._node_queue.put(None)
                break

        print("all results complete")


    async def gather_workers(self):
        root_node = self.root_node
        self.scanned_url_record[get_clean_string_from_URL(root_node.name["URL"])] = True
        self._remaining_node = 1
        await self._node_queue.put(root_node)
        async with aiohttp.ClientSession(trust_env=True,
                                        cookie_jar=aiohttp.CookieJar(),
                                        connector=aiohttp.TCPConnector(
                                            ssl=False,
                                            limit_per_host=self.link_limit
                                        )
                                        ) as session:
            self._session = session
            await asyncio.gather(self._result_worker(), self._header_worker(), 
                                 *(asyncio.create_task(self._tree_grower()) for _ in range(self.worker_size)))
    
    def grow_from_root(self, root_url_object: URL, worker_size):
        self.root_node = Node({
            "URL": root_url_object,
            "title": "root"
        }, parent=None)
        self.gather_queue(worker_size)
        self.scanned_url_record = {}
        asyncio.run(self.gather_workers())

    def gather_queue(self, worker_size):
        self.worker_size = worker_size
        self._node_queue = asyncio.Queue()
        self._branch_queue = asyncio.Queue()
        self._header_queue = asyncio.Queue(worker_size)



    


import orjson
from yarl import URL
from web_scanner_core import WebScanner
from settings import CONNECTION_TIME_OUT, WORKER_SIZE, LINK_PER_HOST, MAX_RETRY
from web_scanner_filters import Filter
from web_scanner_utils import get_sub_host
import random

START_URLS = [
    "https://admission.stanford.edu/",
    "https://college.harvard.edu/guides/application-tips"
]

if __name__ == '__main__':

    ws = WebScanner()
    ft = Filter()

    # configure WebScanner
    ws.connection_time_out = CONNECTION_TIME_OUT
    ws.max_retry = MAX_RETRY
    ws.link_limit = LINK_PER_HOST
    ws.proxy_handler = lambda: f"http://127.0.0.1:3000{random.randint(1,6)}"
    ws.on_dom_tree_ready_filter = ft.check_dom_tree
    ws.on_node_ready_filter = ft.check_node
    ws.on_response_headers_ready_filter = ft.check_response_headers
    ws.on_URL_ready_filter = ft.check_URL

    for url in START_URLS:
        root_url_object = URL(url)
        root_sub_host_string = get_sub_host(root_url_object)
        ft.root_url_object = root_url_object
        ft.root_sub_host_string = root_sub_host_string

        try:
            ws.grow_from_root(root_url_object, WORKER_SIZE)
        except KeyboardInterrupt:
            pass
        finally:
            output_dict = ft.export_target_candidate()
            with open(f"./output/{root_url_object.host}_site_dict.json", 'w+', newline='') as file:
                file.write(orjson.dumps(
                    output_dict, option=orjson.OPT_INDENT_2).decode('utf-8'))


from anytree import Node
from yarl import URL
from web_scanner_filters_utils import limit_depth, limit_random_depth
from web_scanner_core import filter


# Filters are void functions decorated by @filter
# Filters raises AssertionError if the content does not pass the filter
class Filter:
    root_url_object = None
    root_sub_host_string = None
    target_candidate = {}

    title_black_list = [
        ["phd", " graduate", "Graduate"]
    ]

    target_candidate_condition = [
        [" word"],  # and
        ["word limit", "maximum"],  # and
        ["personal", "essay", "question", "statement"],
        ["undergraduate", "student", "first-year"]
    ]

    middleware_condition = [
        ["admission", "application", "apply", "applicant"],
    ]

    host_blacklist_condition = [
        ["news"], ["grad"], ["library"], ["blog"]
    ]

    title_condition = [
        ["admission", "application", "apply", "applicant",
            "requirement", "essay", "prompt", "tip", 
            "personal", "essay", "question", "statement",
            "undergraduate", "student", "first-year"]
    ]

    def __init__(self) -> None:
        pass


    @filter
    def check_node(self, node: Node):
        """
        This function should check everything EXCEPT URLs.
        """
        try:
            title = node.name.get("title")
            assert title
            assert 'root' == title or \
                (self.string_matches_condition_list(self.title_condition, title) and \
                not self.string_matches_condition_list(self.title_black_list, title) \
                )
            assert not title.startswith("grad")
            limit_depth(node)
        except AssertionError:
            limit_random_depth(node)
    


    @filter
    def check_URL(self, node: Node, url_obj: URL):

        html_host = url_obj.host
        assert html_host 
        assert html_host == self.root_url_object.host or html_host.endswith(self.root_sub_host_string) and \
                not self.string_matches_condition_list(self.host_blacklist_condition, html_host)


    @filter
    def check_dom_tree(self, node: Node, lxml_dom_tree):

        # get the plain text from body, excluding the inner texts in <a>
        body_text_xpath = "//body//*[not(self::a)]/text()"
        html_content = ''.join(lxml_dom_tree.xpath(body_text_xpath)).strip()

        assert html_content and len(html_content)
        if self.string_matches_condition_list(self.target_candidate_condition, html_content):

            node.name["is_target_candidate"] = True
            # node.name["text_preview"] = html_content.replace("\t", "").replace("\n", "").replace("  ", "")
            node_data = node.name.copy()
            self.target_candidate[str(node_data.pop('URL'))] = node_data

        else:
            assert self.string_matches_condition_list(self.middleware_condition, html_content)


    @filter
    def check_response_headers(self, node: Node, response):
        assert response.headers.get('content-type'), "no content type"
        assert response.status == 200, f"responded {response.status}"
        assert "text/html" in response.headers.get(
            'content-type'), f"content type: {response.headers.get('content-type')}"


    def string_matches_condition_list(self, condition_words_list, html_content):
        return all(any(condition_word.lower() in html_content.lower()
                    for condition_word in condition_words)
                for condition_words in condition_words_list)

    def export_target_candidate(self) -> dict:
        data = self.target_candidate.copy()
        self.target_candidate.clear()
        return data

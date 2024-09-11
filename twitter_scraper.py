import sys
from progress import Progress
from scroller import Scroller
from tweet import Tweet
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError

from fake_headers import Headers
from time import sleep
import concurrent.futures

from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    NoSuchElementException,
    StaleElementReferenceException,
    WebDriverException,
)
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.service import Service as ChromeService

from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.firefox.service import Service as FirefoxService

from selenium.webdriver.support.ui import WebDriverWait

from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.firefox import GeckoDriverManager

TWITTER_LOGIN_URL = "https://twitter.com/i/flow/login"


class Twitter_Scraper:
    def __init__(
        self,
        tweet_count=50,
        scrape_username="AlexHormozi",
        scrape_poster_details=False,
        scrape_latest=True,
        scrape_top=False,
        proxy=None,
    ):
        print("Initializing Twitter Scraper...")
        self.progress_callback = None
        self.scraped_tweets = 0
        
        self.interrupted = False
        self.tweet_ids = set()
        self.data = []
        self.tweet_cards = []
        self.scraper_details = {
            "type": None,
            "username": None,
            "hashtag": None,
            "query": None,
            "tab": None,
            "poster_details": False,
        }
        self.tweet_count = tweet_count
        self.progress = Progress(0, tweet_count)
        self.router = self.go_to_home
        
        def parallel_setup():
            driver = self._get_driver(proxy=proxy)
            driver.get("https://x.com/home")
            return driver
        
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(parallel_setup)
            self.driver = future.result()
        
        self.actions = ActionChains(self.driver)
        self.scroller = Scroller(self.driver)
        self._config_scraper(
            tweet_count,
            scrape_username,
            scrape_latest,
            scrape_top,
            scrape_poster_details,
        )

        def check_login(driver):
            driver.get("https://x.com/home")
            return "login" not in driver.current_url
        
        is_logged_in = check_login(self.driver)
        
        if is_logged_in:
            print("Already logged in. Skipping login process.")
        else:
            print("Not logged in. Please ensure your Firefox profile contains a logged-in session.")
            self.driver.quit()
            sys.exit(1)


    def _config_scraper(
        self,
        tweet_count=50,
        scrape_username=None,
        scrape_hashtag=None,
        scrape_query=None,
        scrape_latest=True,
        scrape_top=False,
        scrape_poster_details=False,
    ):
        self.tweet_ids = set()
        self.data = []
        self.tweet_cards = []
        self.tweet_count = tweet_count
        self.progress = Progress(0, tweet_count)
        self.scraper_details = {
            "type": None,
            "username": scrape_username,
            "query": scrape_query,
            "tab": "Latest" if scrape_latest else "Top" if scrape_top else "Latest",
            "poster_details": scrape_poster_details,
        }
        self.router = self.go_to_home
        self.scroller = Scroller(self.driver)
        self.router = self.go_to_profile

    def _get_driver(self, proxy=None):
        print("Firefox sürücüsü ayarlanıyor...")
        
        firefox_options = FirefoxOptions()
        
        # Firefox profilinizin yolunu buraya girin
        profile_path = r"C:\Users\ASUS\AppData\Roaming\Mozilla\Firefox\Profiles\9pyz9nno.default-release"
        firefox_options.add_argument("-profile")
        firefox_options.add_argument(profile_path)
        firefox_options.add_argument("--headless")
        
        if proxy:
            firefox_options.add_argument(f'--proxy-server={proxy}')
        
        try:
            service = FirefoxService(GeckoDriverManager().install())
            driver = webdriver.Firefox(service=service, options=firefox_options)
            print("Firefox sürücüsü başarıyla başlatıldı.")
            return driver
        except Exception as e:
            print(f"Firefox sürücüsü başlatılırken hata oluştu: {e}")
            raise
 


    def go_to_home(self):
        self.driver.get("https://twitter.com/home")
        sleep(3)
        pass

    def go_to_profile(self):
        self.driver.get(f"https://twitter.com/{self.scraper_details['username']}")
        sleep(3)
        pass


    def get_tweet_cards(self):
        self.tweet_cards = self.driver.find_elements(
            "xpath", '//article[@data-testid="tweet" and not(@disabled)]'
        )
        pass


    async def scrape_tweets(
        self,
        tweet_count=50,
        no_tweets_limit=False,
        scrape_username=None,
        scrape_hashtag=None,
        scrape_query=None,
        scrape_latest=True,
        scrape_top=False,
        scrape_poster_details=False,
        router=None,
        progress_callback=None,
    ):
        self.progress_callback = progress_callback
        self.scraped_tweets = 0
        self._config_scraper(
            tweet_count,
            scrape_username,
            scrape_hashtag,
            scrape_query,
            scrape_latest,
            scrape_top,
            scrape_poster_details,
        )

        if router is None:
            router = self.router

        router()

        print("Scraping Tweets from @{}...".format(self.scraper_details["username"]))

        # Accept cookies to make the banner disappear
        try:
            accept_cookies_btn = self.driver.find_element(
            "xpath", "//span[text()='Refuse non-essential cookies']/../../..")
            accept_cookies_btn.click()
        except NoSuchElementException:
            pass

        self.progress.print_progress(0, False, 0, no_tweets_limit)

        refresh_count = 0
        added_tweets = 0
        empty_count = 0
        retry_cnt = 0

        while self.scroller.scrolling:
            try:
                self.get_tweet_cards()
                added_tweets = 0

                for card in self.tweet_cards[-15:]:
                    try:
                        tweet_id = str(card)

                        if tweet_id not in self.tweet_ids:
                            self.tweet_ids.add(tweet_id)

                            if not self.scraper_details["poster_details"]:
                                self.driver.execute_script(
                                    "arguments[0].scrollIntoView();", card
                                )

                            tweet = Tweet(
                                card=card,
                                driver=self.driver,
                                actions=self.actions,
                            )

                            if tweet:
                                if not tweet.error and tweet.tweet is not None:
                                    if not tweet.is_ad:
                                        self.data.append(tweet.tweet)
                                        added_tweets += 1
                                        self.scraped_tweets += 1
                                        self.progress.print_progress(len(self.data), False, 0, no_tweets_limit)
                                        if self.progress_callback:
                                            await self.progress_callback(self.scraped_tweets, self.tweet_count)

                                        if len(self.data) >= self.tweet_count and not no_tweets_limit:
                                            self.scroller.scrolling = False
                                            break
                                    else:
                                        continue
                                else:
                                    continue
                            else:
                                continue
                        else:
                            continue
                    except NoSuchElementException:
                        continue

                if len(self.data) >= self.tweet_count and not no_tweets_limit:
                    break

                if added_tweets == 0:
                    try:
                        while retry_cnt < 15:
                            retry_button = self.driver.find_element(
                            "xpath", "//span[text()='Retry']/../../..")
                            self.progress.print_progress(len(self.data), True, retry_cnt, no_tweets_limit)
                            sleep(58)
                            retry_button.click()
                            retry_cnt += 1
                            sleep(2)
                    # There is no Retry button so the counter is reseted
                    except NoSuchElementException:
                        retry_cnt = 0
                        self.progress.print_progress(len(self.data), False, 0, no_tweets_limit)

                    if empty_count >= 5:
                        if refresh_count >= 3:
                            print()
                            print("No more tweets to scrape")
                            break
                        refresh_count += 1
                    empty_count += 1
                    sleep(1)
                else:
                    empty_count = 0
                    refresh_count = 0
            except StaleElementReferenceException:
                sleep(2)
                continue
            except KeyboardInterrupt:
                print("\n")
                print("Keyboard Interrupt")
                self.interrupted = True
                break
            except Exception as e:
                print("\n")
                print(f"Error scraping tweets: {e}")
                break

        print("")

        if len(self.data) >= self.tweet_count or no_tweets_limit:
            print("Scraping Complete")
        else:
            print("Scraping Incomplete")

        if not no_tweets_limit:
            print("Tweets: {} out of {}\n".format(len(self.data), self.tweet_count))

        pass

    def save_to_db(self):
        print("Saving Tweets to DB...")

        client = MongoClient("mongodb://root:p2f9FXGxhdmPtEp8rmOv6ykKm0v8i1FNTmBWUqcDk9O0BiDsAzlDdQCLYQKuFc4R@95.217.39.116:5424/?directConnection=true")
    
        db_name = "Tweets"

        if db_name not in client.list_database_names():
            print(f"Creating '{db_name}' database...")
        else:
            print(f"Connecting to '{db_name}' database...")
        
        db = client[db_name]

        collection_name = f"{self.scraper_details['username']}"
    
        if collection_name not in db.list_collection_names():
            print(f"Creating '{collection_name}' collection...")
            db.create_collection(collection_name)
        else:
            print(f"Connecting to '{collection_name}' collection...")
        
        collection = db[collection_name]

        tweets = []
        for tweet in self.data:
            tweet_data = {
                "Content": tweet[0],
                "Photos": tweet[1],
                "Tweet Link": tweet[2],
                "Timestamp": tweet[3],
                "Comments": tweet[4],
                "Retweets": tweet[5],
                "Likes": tweet[6],
                "Analytics": tweet[7],
            }
            tweet_data["_id"] = tweet_data["Tweet Link"].split("/")[-1]
            tweets.append(tweet_data)

        print("Number of tweets: ", len(tweets))

        for tweet in tweets:
            try:
                collection.insert_one(tweet)
                print(f"New tweet added: {tweet['Tweet Link']}")
            except DuplicateKeyError:
                update_data = {
                    "Comments": tweet["Comments"],
                    "Retweets": tweet["Retweets"],
                    "Likes": tweet["Likes"],
                    "Analytics": tweet["Analytics"]
                }
                collection.update_one({"_id": tweet["_id"]}, {"$set": update_data})
                print(f"Existing tweet updated: {tweet['Tweet Link']}")


"""
This script will visit podcasti.si and fetch all episodes and podcasts
available. The result is a figure showing `TOP_N` podcasts and their
published episodes in time.
"""

import datetime
import time

import pandas as pd
from plotnine import (
    aes,
    ggplot,
    ggsave,
    geom_line,
    geom_point,
    geom_vline,
    scale_color_brewer,
    scale_y_discrete,
    theme,
    theme_bw,
    xlab,
    ylab,
)
import requests

today = datetime.datetime.now()
TOP_N = 70
OUTPUT_FIG = f"podcast_history_{today.year}-{today.month}"
episodes_url = "https://podcasti.si/api/episodes/?limit=5000&offset=0"
podcasts_url = "https://podcasti.si/api/podcasts/?limit=1000&offset=0"

# Fetch episodes
eps = pd.DataFrame()
while True:
    rsp = requests.get(url=episodes_url).json()

    res = pd.DataFrame(rsp["results"])
    eps = pd.concat([eps, res])

    episodes_url = rsp["next"]
    time.sleep(2)

    if rsp["next"] is None:
        break

# Fetch podcasts
pods = pd.DataFrame()
while True:
    rsp = requests.get(url=podcasts_url).json()

    res = pd.DataFrame(rsp["results"])
    pods = pd.concat([pods, res])

    podcasts_url = rsp["next"]
    time.sleep(2)

    if rsp["next"] is None:
        break

episodes = eps[["id", "title", "created_datetime", "published_datetime", "podcast"]]
podcasts = pods[["name", "id", "is_radio"]].set_index("id")

episodes = episodes.join(other=podcasts, on=["podcast"]).copy()
episodes.loc[:, "created_datetime"] = pd.to_datetime(
    episodes.loc[:, "created_datetime"]
)
episodes.loc[:, "published_datetime"] = pd.to_datetime(
    episodes.loc[:, "published_datetime"]
)

top_pods = (
    episodes[["id", "name"]]
    .groupby("name")
    .count()
    .sort_values(by="id", ascending=False)
)
top_pods.columns = ["count"]
first_ep = episodes[["name", "published_datetime"]].groupby("name").min()
top_pods = top_pods.join(other=first_ep)

top_pods = top_pods.sort_values(by=["published_datetime", "count"], ascending=True)

top_pods = top_pods.iloc[:TOP_N]

eps_top = episodes[[x in top_pods.index for x in episodes["name"]]].copy()
eps_top["name"] = pd.Categorical(
    values=eps_top["name"], categories=top_pods.index[::-1]
)
eps_top.to_csv("podcasts.csv", sep=";")

fig = (
    ggplot(eps_top, mapping=aes("published_datetime", "name", color="is_radio"))
    + theme_bw()
    + theme(legend_position=None)
    + xlab("Datum objave")
    + ylab("Ime podkasta")
    + scale_color_brewer(type="qual", palette="Accent", guide=False)
    + scale_y_discrete()
    + geom_vline(
        data=pd.DataFrame({"datum": [datetime.datetime.now()]}),
        mapping=aes(xintercept="datum"),
        linetype="dotted",
    )
    + geom_line(alpha=0.5)
    + geom_point(size=2, shape="|", alpha=0.75)
)
ggsave(fig, filename=OUTPUT_FIG, width=15, height=10, dpi=130)

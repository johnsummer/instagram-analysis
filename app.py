from itertools import count
import requests
import pandas as pd

from datetime import datetime as dt
from dateutil import tz

import altair as alt
import streamlit as st

from configparser import ConfigParser
import os

base_url = "https://graph.facebook.com/v13.0/"

media_fields = 'timestamp,like_count,comments_count'
count_default = 25

business_account_id = None
access_token = None

config_path = "secret/config.ini"
if os.path.exists(config_path):
    config = ConfigParser()
    config.read(config_path)

    section = 'meta_app_info'

    business_account_id = config.get(section, 'business_account_id')
    access_token = config.get(section, 'access_token')

@st.cache
def get_media(username, count=count_default, business_account_id=business_account_id, access_token=access_token):
    request_url = (
        base_url + business_account_id 
        + "?fields=business_discovery.username({username}){{media{{{media_fields}}}}}&access_token={access_token}"
        .format(username=username,media_fields=media_fields,access_token=access_token)
    )

    response = requests.get(request_url)
    result = response.json()

    media_list = result['business_discovery']['media']['data']
    df_media = pd.DataFrame(media_list)

    # データ整形
    df_media['timestamp'] = [m.replace('+0000', '+0900') for m in df_media['timestamp']]
    df_media = df_media[['timestamp', 'like_count', 'comments_count']]

    return df_media

try:
    st.title("インスタグラム分析ツール")

    username = st.sidebar.text_input("分析対象のインスタグラムユーザ名")
    if business_account_id is None:
        business_account_id = st.sidebar.text_input("Instagram APIを使うためのビジネスアカウントID")
    
    if access_token is None:
        access_token = st.sidebar.text_input("Instagram APIを使うためのアクセストークン")

    if (not username) or (not business_account_id) or (not access_token):
        st.text("サイトバーにある項目を入力するとグラフを表示します。")
    else:
        df_media = get_media(username=username, business_account_id=business_account_id, access_token=access_token)

        st.write("""### {username}の投稿のいいね数、コメント数の傾向""".format(username=username))

        histgram_like =(
            alt.Chart(df_media)
            .mark_bar(opacity=0.8, clip=True, color='orange')
            .encode(
                x=alt.X("timestamp:T", title='日付'),
                y=alt.Y("like_count:Q", stack=None, title='いいね')
            )
        ).properties(
            width=600
        )

        ymax = df_media['comments_count'].max()

        circle_comments = (
            alt.Chart(df_media)
            .mark_circle(size=60)
            .encode(
                alt.X("timestamp:T", title='日付'),
                y=alt.Y("comments_count:Q", stack=None, title='コメント', scale=alt.Scale(domain=[0, ymax + 2]))
            )
        ).properties(
            width=600
        )

        chart = alt.layer(histgram_like, circle_comments).resolve_scale(
            y = 'independent'
        )

        st.altair_chart(chart, use_container_width=True)

except:
    st.error("エラーが発生しました")
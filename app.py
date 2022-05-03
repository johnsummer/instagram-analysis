from itertools import count
import requests
import pandas as pd

from datetime import datetime as dt
from dateutil import tz

import altair as alt
import streamlit as st

from configparser import ConfigParser
import os

# 共通変数

base_url = "https://graph.facebook.com/v13.0/"

media_fields = 'timestamp,like_count,comments_count'
insight_metric = 'reach'
count_default = 25

business_account_id = None
access_token = None

# ローカルでテストしやすくするために、ローカルに保存している認証情報。
# Webで実行する際はこの認証用のファイルが存在しないため、ビジネスアカウントIDとアクセストークンの入力が求められる

config_path = "secret/config.ini"
if os.path.exists(config_path):
    config = ConfigParser()
    config.read(config_path)

    section = 'meta_app_info_main'

    business_account_id = config.get(section, 'business_account_id')
    access_token = config.get(section, 'access_token')

# メディア(投稿)リストを取得する
@st.cache(allow_output_mutation=True)
def get_media_list(username, count=count_default, business_account_id=business_account_id, access_token=access_token):
    request_url = (
        base_url + business_account_id 
        + "?fields=business_discovery.username({username}){{media{{{media_fields}}}}}&access_token={access_token}"
        .format(username=username,media_fields=media_fields,access_token=access_token)
    )

    response = requests.get(request_url)
    result = response.json()

    media_list = result['business_discovery']['media']['data']
    return media_list
    
# メディア(投稿)リストを基にメディアごとのインサイト情報を取得する
@st.cache
def get_insight_of_media(media_list, metric=insight_metric):
    media_list_insight = []

    for media in media_list:
        request_url = base_url + media['id'] + '/insights?metric={metric}&access_token={access_token}'.format(metric=metric,access_token=access_token)
        response = requests.get(request_url)
        result = response.json()['data'][0]['values'][0]['value']
        media.update([('reach', result)])
        media_list_insight.append(media)

    return media_list_insight

# 日本時間になるようにタイムスタンプの文字列を整形する
def sharp_dataframe_data(df_media):

    # 日本時間に変換する
    df_media['timestamp'] = [m.replace('+0000', '+0900') for m in df_media['timestamp']]

    return df_media

# メイン処理
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
        media_list = get_media_list(username=username, business_account_id=business_account_id, access_token=access_token)
        media_list = get_insight_of_media(media_list=media_list)
        # print(media_list)
        df_media = pd.DataFrame(media_list)
        df_media = sharp_dataframe_data(df_media)

        st.write("""### {username}の投稿のいいね数、コメント数の傾向""".format(username=username))

        # いいねの傾向
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

        # コメントの傾向
        ymax_comment = df_media['comments_count'].max() + 2

        line_comments = (
            alt.Chart(df_media)
            .mark_line(opacity=0.8, clip=True, point=True)
            .encode(
                x=alt.X("timestamp:T", title='日付'),
                y=alt.Y("comments_count:Q", stack=None, title='コメント', scale=alt.Scale(domain=[0, ymax_comment]))
            )
        ).properties(
            width=600
        )

        # いいね、コメントを重ねたグラフ
        chart1 = alt.layer(histgram_like, line_comments).resolve_scale(
            y = 'independent'
        )

        st.altair_chart(chart1, use_container_width=True)

        ymax_like_day = (df_media['like_count'].mean() + df_media['like_count'].max()) / 2

        histgram_like_day =(
            alt.Chart(df_media)
            .mark_bar(opacity=0.8, clip=True, color='orange')
            .encode(
                x=alt.X('day(timestamp):O', title='曜日'),
                y=alt.Y('mean(like_count):Q', stack=None, title='いいね', scale=alt.Scale(domain=[0, ymax_like_day]))
            )
        ).properties(
            width=600
        )

        st.altair_chart(histgram_like_day, use_container_width=True)

        st.write("""### {username}の投稿のいいね数、リーチ数の傾向""".format(username=username))

        # メディアごとのリーチの傾向
        line_reach =(
            alt.Chart(df_media)
            .mark_line(opacity=0.8, clip=True, point=True)
            .encode(
                x=alt.X("timestamp:T", title="日付"),
                y=alt.Y("reach:Q", stack=None, title="リーチ")    
            )
        ).properties(
            width=600
        )

        # いいね、リーチを重ねたグラフ
        chart2 = alt.layer(histgram_like, line_reach).resolve_scale(
            y = 'independent'
        )

        st.altair_chart(chart2, use_container_width=True)
except:
    st.error("エラーが発生しました")
import streamlit as st
# To make things easier later, we're also importing numpy and pandas for
# working with sample data.
import pandas as pd
import numpy as np
import requests
from pycoingecko import CoinGeckoAPI
import datetime
import time
import altair as alt
from altair.expr import datum, if_


cg = CoinGeckoAPI()

@st.cache
def get_price(coin):
    price_dict = cg.get_price(ids=coin, vs_currencies='usd')
    return price_dict[coin]['usd']


@st.cache
def get_history(coin):

    coin_history = cg.get_coin_market_chart_by_id(id=coin, vs_currency='usd', days='max')

    days = [i[0] for i in coin_history['prices']]
    days = pd.to_datetime(days, unit='ms')

    prices = [i[1] for i in coin_history['prices']]

    days = days[:-1]
    prices = prices[:-1]

    data = {'date': days, 'price': prices}
    df = pd.DataFrame(data={'price': prices}, index=days)
    
    return df


choices = ['Bitcoin', 'Ethereum', 'Chainlink', 'Polkadot', 'Cardano', 'Avalanche', "About"]

df_choice = st.sidebar.radio('Currency', choices)

if df_choice:
    if df_choice == "About":
        
        st.markdown('''

        # Hey There!

        This is your friend Motlaq, a data analyst and a fellow crypto investor. This website is a way to look at some cryptocurrencies from a data science point of view.
        The charts here are heavily inspired by [Benjamin Cowen's youtube channel](https://www.youtube.com/channel/UCRvqjQPSeaWn-uEx-w0XOIg). Do yourself a favor and subscribe to his channel.
        In fact, the ideas behind a lot of the charts here are originally Benjamin's and I'm only making an interactive always-updated virsions of them. 
        Make no mistake, this is a work in progress and you're likely to see changes soon so make sure you leave feedback [on Telegram](https://t.me/motlaaq)
        . Lastly, I have no intention to monetize this. But you can always [buy me a coffee](https://www.buymeacoffee.com/Motlaq)
        if you find this website useful!

        ---

        ''')
    if df_choice != "About":
        st.title('{} Charts'.format(df_choice))
        st.markdown('---')
        price = get_price(df_choice.lower())
        texty = st.empty()
        BTC_priceW = get_history('bitcoin')
        if df_choice == 'Avalanche':
            currency_hist = get_history('avalanche-2') #df
        elif df_choice == 'Bitcoin':
            currency_hist = BTC_priceW
        else:
            currency_hist = get_history(df_choice.lower()) #df

        currency_hist = currency_hist.join(BTC_priceW, lsuffix='_x', rsuffix='_BTC')
        weekly_dates = pd.date_range(currency_hist.index[0], currency_hist.index[-1], freq='W').to_series() # Generate a list of weeks
        BTC_priceW = BTC_priceW[BTC_priceW.index.isin(weekly_dates)]
        BTC_priceW['week_number'] = BTC_priceW.index.isocalendar().week
        BTC_priceW['20W MA'] = BTC_priceW.iloc[:,0].rolling(window=20).mean() # 20 Week Moving Average
        BTC_priceW['year'] = BTC_priceW.index.year
        BTC_priceW['weekyear'] = BTC_priceW[['week_number', 'year']].astype(str).apply(''.join, axis=1)
        
        currency_hist['week_number'] = currency_hist.index.isocalendar().week
        currency_hist['year'] = currency_hist.index.year
        currency_hist['weekyear'] = currency_hist[['week_number', 'year']].astype(str).apply(''.join, axis=1)
        

        currency_hist_20WBTC = pd.merge(currency_hist.reset_index(), BTC_priceW, on='weekyear', how='outer')
        currency_hist_20WBTC['20W MA'].fillna(method='ffill', inplace=True)
        currency_hist_20WBTC['week_number_y'].fillna(method='ffill', inplace=True)
        currency_hist_20WBTC['price_BTC'].fillna(method='ffill', inplace=True)

        currency_hist['20D MA'] = currency_hist.iloc[:,0].rolling(window=20).mean()
        currency_hist['% extension from 20D MA'] = ((currency_hist['price_x']-currency_hist['20D MA'])/currency_hist['price_x'])*100
        MA_20D = currency_hist['price_x'][-20:].mean()
        st.header('Historical Price')
        texty = st.text("current price: ${}".format(price))
        
        # currency_hist_20WBTC['price above 20D MA'] = currency_hist_20WBTC['price_x'] > currency_hist_20WBTC['20D MA']
        currency_hist_20WBTC['price above BTC 20W MA'] = currency_hist_20WBTC['price_BTC'] > currency_hist_20WBTC['20W MA']
        currency_hist_20WBTC['BTC above 20W MA'] = np.where(currency_hist_20WBTC['price above BTC 20W MA']!= 0, 'Above', 'Below')
        #st.write(currency_hist_20WBTC)
        #currency_hist['men_women'] = population['sex'].map({1: 'Men', 2: 'Women'})
        if st.checkbox('show price color coded by wether Bitcoin is above/below the 20 Week moving average'):
            chart = alt.Chart(currency_hist_20WBTC.reset_index(), title="{} Price vs Time".format(df_choice)).mark_circle(size=70, opacity=0.6).encode(
                alt.X('index', axis=alt.Axis(title='Date')),
                alt.Y('price_x',axis=alt.Axis(title='Price'), scale=alt.Scale(type='log')),
                color=alt.Color('price above BTC 20W MA',scale=alt.Scale(scheme='category20'), legend=alt.Legend(title="BTC Price"))).transform_calculate(
            'price above BTC 20W MA', if_(datum['price above BTC 20W MA'] == 0, 'BTC Below 20 Week MA', 'BTC Above 20 Week MA')).interactive()

            #st.line_chart(currency_hist['price'])
            st.altair_chart(chart, use_container_width=True)   
        else:
            line_chart = alt.Chart(currency_hist_20WBTC.reset_index(), title="{} Price vs Time".format(df_choice)).mark_line().encode(
                alt.X('index', axis=alt.Axis(title='Date')),
                alt.Y('price_x',axis=alt.Axis(title='Price'), scale=alt.Scale(type='log'))).interactive()
            
            st.altair_chart(line_chart, use_container_width=True)

        if df_choice == "Bitcoin":
            st.header("BTC vs US Dollar Index")
            # BTCDXY = BTCDXYChart()
            # st.altair_chart(BTCDXY, use_container_width=True)
            
            DXY = pd.read_csv('DXY.csv', index_col='Date')
            DXY.rename(columns={'Price':'price'}, inplace=True)
            btc = get_history('bitcoin')
            dxybtc = btc.join(DXY, lsuffix='_BTC', rsuffix='_DXY', how='inner')

            base = alt.Chart(dxybtc.reset_index(), title='Bitcoin Price vs US Dollar Index').encode(
                alt.X('index', title=None))

            btcline = base.mark_line(color='orange').encode(
                    alt.Y('price_BTC', scale=alt.Scale(type='log'), axis=alt.Axis(title='BTC Price', titleColor='orange')),
                    tooltip=['price_BTC', 'price_DXY']).interactive()

            dxyline = base.mark_line(color='#57A44C').encode(
                    alt.Y('price_DXY', axis=alt.Axis(title='DXY', titleColor='#57A44C'), scale=alt.Scale(domain=[75,110])),
                    tooltip=['price_BTC', 'price_DXY']).interactive()

            btcdxychart = alt.layer(btcline, dxyline).resolve_scale(
                y='independent')

            st.altair_chart(btcdxychart, use_container_width=True)




        st.markdown('---')
        st.header("Charts, Charts, Charts!")
        charts_options = ["Topic", "20D Extenstion", "Annual price", "When BTC drops..."]
        chart_box = st.selectbox("Choose a topic", charts_options)
        if chart_box == "20D Extenstion":
            # if df_choice == "Bitcoin":
            #     st.info("Coming Soon! (spoiler: Nothing impressive here for Bitcoin, Ethereum")
            st.header('Extenstion from the 20 Day Moving Average')
            st.text("20D MA: ${:.3f}".format(MA_20D))
            #st.line_chart(currency_hist['% extension from 20D MA'])
            #st.write(currency_hist)


            pts = alt.selection(type="interval", encodings=["x"])

            extension = alt.Chart(currency_hist.reset_index(), width=630, title="{}'s Extension from 20 Day Moving Average".format(df_choice)).mark_line().encode(
                alt.X('index', axis=alt.Axis(title='Date')), alt.Y('% extension from 20D MA'),
                tooltip=['index', 'price_x', '20D MA', '% extension from 20D MA']
                
            ).transform_filter(pts).interactive()
            
            currency_hist['Zeros'] = 0
            zero_extension = alt.Chart(currency_hist).mark_rule(size=2, color='gray').encode(
                
                alt.Y('Zeros', axis=alt.Axis(title='Extension from 20D MA (%)'))
            )
            
            ss = extension + zero_extension
            #st.altair_chart(ss, use_container_width=True)
            
            
            #st.write(currency_hist_20WBTC)
            aa = alt.Chart(currency_hist_20WBTC.reset_index(), width=630, title="BTC vs its 20W MA").mark_tick().encode(
                    alt.X('index', title='Date'),
                    alt.Y('BTC above 20W MA', title=None, axis=alt.Axis(values=["Below", "Above"])),
                    color=alt.condition(pts, alt.value("black"), alt.value("lightgray"))

                ).add_selection(pts)

            aaa = alt.vconcat(ss, aa).resolve_legend(color='independent', size='independent')

            aaaa = st.altair_chart(aaa, use_container_width=True)
            #st.line_chart(currency_hist['ln(price/20D MA)'])
    
        elif chart_box == "Annual price":

            if df_choice == "Avalanche" or df_choice == "Polkadot":
                st.warning("Chart not available - Not enough data")
            else: 
                coin_df = pd.read_csv('{}_annual_price.csv'.format(df_choice.lower()))

                annual_chart_line = alt.Chart(coin_df.reset_index()).mark_line().encode(
                    alt.X('year:N'),
                    alt.Y('price', axis=alt.Axis(title='Average Price'), scale=alt.Scale(type='log'))).interactive()

                annual_chart_circle = alt.Chart(coin_df.reset_index()).mark_point(size=60).encode(
                    alt.X('year:N'),
                    alt.Y('price', scale=alt.Scale(type='log')),
                    tooltip=['year', 'price']).interactive()

                annual_chart = annual_chart_line + annual_chart_circle
                st.header("{} Annual Price".format(df_choice))
                st.altair_chart(annual_chart, use_container_width=True)
        
        elif chart_box == "When BTC drops...":
            if df_choice == 'Ethereum':
                st.header("When BTC drops 10%...")
                BTCETH10drop = pd.read_csv('BTCETH10drop_V2.csv', index_col=0)

                BTCETH10 = alt.Chart(BTCETH10drop.reset_index(), title="When Bitcoin drops 10%, what does {} do?".format(df_choice)).mark_bar().encode(
                alt.X('yearmonthdate(index):N', title="Date"),
                alt.Y('{} price percent diff'.format(df_choice), axis=alt.Axis(title="{} price drop (%)".format(df_choice))),
                tooltip=['BTC price percent diff', '{} price percent diff'.format(df_choice.capitalize())],
                color=alt.Color('{} dropped more'.format(df_choice), scale=alt.Scale(scheme='paired'), legend=alt.Legend(title="Drop compared to BTC"))).transform_calculate(
                    '{} dropped more'.format(df_choice), if_(datum['{} dropped more'.format(df_choice)] == 0, 'Less', 'More')).interactive()

            
                st.altair_chart(BTCETH10, use_container_width=True)


                ######################## 20% drop ########################


                st.header("When BTC drops 20%...")
                BTCETH20drop = pd.read_csv('BTCETH20drop_V2.csv', index_col=0)

                BTCETH20 = alt.Chart(BTCETH20drop.reset_index(), title="When Bitcoin drops 20%, what does {} do?".format(df_choice)).mark_bar().encode(
                alt.X('yearmonthdate(index):N', title="Date"),
                alt.Y('{} price percent diff'.format(df_choice), axis=alt.Axis(title="{} price drop (%)".format(df_choice))),
                tooltip=['BTC price percent diff', '{} price percent diff'.format(df_choice.capitalize())],
                color=alt.Color('{} dropped more'.format(df_choice), scale=alt.Scale(scheme='paired'), legend=alt.Legend(title="Drop compared to BTC"))).transform_calculate(
                    '{} dropped more'.format(df_choice), if_(datum['{} dropped more'.format(df_choice)] == 0, 'Less', 'More')).interactive()

            
                st.altair_chart(BTCETH20, use_container_width=True)


                ######################## Another coin ########################

            elif df_choice == 'Chainlink':
                

                st.header("When BTC drops 10%...")
                BTCLINK10drop = pd.read_csv('BTClink10drop_V2.csv', index_col=0)

                BTCLINK10 = alt.Chart(BTCLINK10drop.reset_index(), title="When Bitcoin drops 10%, what does {} do?".format(df_choice)).mark_bar().encode(
                alt.X('yearmonthdate(index):N', title="Date"),
                alt.Y('{} price percent diff'.format(df_choice), axis=alt.Axis(title="{} price drop (%)".format(df_choice))),
                tooltip=['BTC price percent diff', '{} price percent diff'.format(df_choice.capitalize())],
                color=alt.Color('{} dropped more'.format(df_choice), scale=alt.Scale(scheme='paired'), legend=alt.Legend(title="Drop compared to BTC"))).transform_calculate(
                    '{} dropped more'.format(df_choice), if_(datum['{} dropped more'.format(df_choice)] == 0, 'Less', 'More')).interactive()


                # BTCLINK = alt.Chart(BTCLINK20drop.reset_index(), title="When Bitcoin drops 20%, what does LINK do?").mark_bar().encode(
                # alt.X('Date'),
                # alt.Y('LINK 1W change percent', axis=alt.Axis(title="LINK price drop (%)")),
                # tooltip=['BTC 1W change percent', 'LINK 1W change percent'],
                # color=alt.Color('LINK dropped more', scale=alt.Scale(scheme='paired'), legend=alt.Legend(title="Drop compared to BTC"))).transform_calculate(
                #     'LINK dropped more', if_(datum['LINK dropped more'] != 0, 'More', 'Less')).interactive()

                st.altair_chart(BTCLINK10, use_container_width=True)

                ######################## 20% drop ########################
                
                st.header("When BTC drops 20%...")
                BTCLINK20drop = pd.read_csv('BTClink20drop_V2.csv', index_col=0)

                BTCLINK20 = alt.Chart(BTCLINK20drop.reset_index(), title="When Bitcoin drops 20%, what does {} do?".format(df_choice)).mark_bar().encode(
                alt.X('yearmonthdate(index):N', title="Date"),
                alt.Y('{} price percent diff'.format(df_choice), axis=alt.Axis(title="{} price drop (%)".format(df_choice))),
                tooltip=['BTC price percent diff', '{} price percent diff'.format(df_choice.capitalize())],
                color=alt.Color('{} dropped more'.format(df_choice), scale=alt.Scale(scheme='paired'), legend=alt.Legend(title="Drop compared to BTC"))).transform_calculate(
                    '{} dropped more'.format(df_choice), if_(datum['{} dropped more'.format(df_choice)] == 0, 'Less', 'More')).interactive()

                st.altair_chart(BTCLINK20, use_container_width=True)

                ######################## Another coin ########################

            elif df_choice == 'Cardano':
                
                st.header("When BTC drops 10%...")
                BTCADA10drop = pd.read_csv('BTCADA10drop_V2.csv', index_col=0)

                BTCADA10 = alt.Chart(BTCADA10drop.reset_index(), title="When Bitcoin drops 10%, what does {} do?".format(df_choice)).mark_bar().encode(
                alt.X('yearmonthdate(index):N', title="Date"),
                alt.Y('{} price percent diff'.format(df_choice), axis=alt.Axis(title="{} price drop (%)".format(df_choice))),
                tooltip=['yearmonthdate(index)', 'BTC price percent diff', '{} price percent diff'.format(df_choice.capitalize())],
                color=alt.Color('{} dropped more'.format(df_choice), scale=alt.Scale(scheme='paired'), legend=alt.Legend(title="Drop compared to BTC"))).transform_calculate(
                    '{} dropped more'.format(df_choice), if_(datum['{} dropped more'.format(df_choice)] == 0, 'Less', 'More')).interactive()

                st.altair_chart(BTCADA10, use_container_width=True)

                ######################## 20% drop ########################

                st.header("When BTC drops 20%...")
                BTCADA20drop = pd.read_csv('BTCADA20drop_V2.csv', index_col=0)

                BTCADA20 = alt.Chart(BTCADA20drop.reset_index(), title="When Bitcoin drops 20%, what does {} do?".format(df_choice)).mark_bar().encode(
                alt.X('yearmonthdate(index):N', title="Date"),
                alt.Y('{} price percent diff'.format(df_choice), axis=alt.Axis(title="{} price drop (%)".format(df_choice))),
                tooltip=['yearmonthdate(index)', 'BTC price percent diff', '{} price percent diff'.format(df_choice.capitalize())],
                color=alt.Color('{} dropped more'.format(df_choice), scale=alt.Scale(scheme='paired'), legend=alt.Legend(title="Drop compared to BTC"))).transform_calculate(
                    '{} dropped more'.format(df_choice), if_(datum['{} dropped more'.format(df_choice)] == 0, 'Less', 'More')).interactive()

                
                st.altair_chart(BTCADA20, use_container_width=True)








                #st.write(BTCADA20drop)
                    # BTCADA = alt.Chart(BTCADA20drop.reset_index(), title="When Bitcoin drops 20%, what does Cardano do?").mark_bar().encode(
                    # alt.X('Date'),
                    # alt.Y('ADA 1W change percent', axis=alt.Axis(title="ADA price drop (%)")),
                    # alt.Color('ADA dropped more', scale=alt.Scale(scheme='paired'), legend=alt.Legend(title="Drop compared to BTC")),
                    # tooltip=['BTC 1W change percent', 'ADA 1W change percent']).transform_calculate(
                    #     'ADA dropped more', if_(datum['ADA dropped more'] != 0, 'More', 'Less')).interactive()

                

            else:
                st.warning("This chart is only available for Ethereum, Chainlink or Cardano.")






Ben_statememnts = [
    "I don't consider Ethereum an altcoin",

    "It's not about return, it's about your risk adjusted return",
    
    "I can't tell you what's gonna happen in the short term I just try to react to it",
    
    "Remember it's better to accumulate a coin when it's going quiet not when it's going parabolic",
    
    "If btc makes sideways action, then expect altcoins to start running again",
    
    "It's all fun and games until you wake up one day and you're down 20 or 30%" ,
    
    "Getting your portfolio in a position where you can handle all three scenarios is the way to win in crypto",
    
    "The main reason I hold LINK is: its negative volatility is offset by Bitcoin positive volatility",
    
    "You'll never go broke taking profits",
    
    "You'll never go broke taking profits",
    
    "We need Ethereum to outperform Bitcoin in order to justify holding it",
    
    "Expecting an immediate ROI is pretty much gambling",
    
    "I think if you're in crypto, I think the majority of your portfolio should be in Bitcoin",
    
    "The faster you get to thinking of crypto in terms of more than USD, the better. we look at Ethereum and LINK in terms of Bitcoin not just USD. this will help you understand what???s going on and be intuitive about what to do",
    
    "The goal is to time momentum shifts in the market not chase pumps",
    
    "The focus is to slowly move in and out, not pretend like we can time bottoms and tops",
]


randnum = np.random.randint(len(Ben_statememnts))
statement = Ben_statememnts[randnum]
st.sidebar.markdown("---")
st.sidebar.write("> {} --  **Benjamin Cowen** ".format(statement))
st.sidebar.markdown("")



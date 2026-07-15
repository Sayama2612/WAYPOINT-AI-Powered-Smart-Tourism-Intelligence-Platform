import streamlit as st
from pathlib import Path
import pandas as pd
import numpy as np
import plotly.express as px
from models.recommender import ContentRecommender
from services.auth import is_admin_user
from services.db import save_export_file

st.set_page_config(page_title="WAYPOINT — AI Smart Tourism", layout="wide")

BASE = Path(__file__).parent

st.sidebar.title("WAYPOINT")
# load remembered username if present
from services.auth import get_last_user, set_last_user, initiate_magic_link, verify_magic_link, get_user_from_session
remembered = get_last_user()
session_id = st.session_state.get('session_id', '')
user_name = ''
if session_id:
    # validate session
    user_name = get_user_from_session(session_id) or ''

if not user_name:
    # show magic-link login UI, fall back to username text input
    email_input = st.sidebar.text_input('Email (for magic link)', value='')
    if st.sidebar.button('Send magic link') and email_input:
        res = initiate_magic_link(email_input)
        if res.get('ok'):
            # display the magic link (simulated send)
            st.sidebar.success('Magic link created — paste token or open link')
            st.sidebar.write(res.get('link'))
            st.session_state['last_magic_token'] = res.get('token')
        else:
            st.sidebar.error('Failed to create magic link')
    token_input = st.sidebar.text_input('Paste magic token (or open link)')
    if st.sidebar.button('Verify token') and token_input:
        v = verify_magic_link(token_input)
        if v.get('ok'):
            st.session_state['session_id'] = v.get('session_id')
            user_name = v.get('user')
            st.sidebar.success(f'Logged in as {user_name}')
        else:
            st.sidebar.error('Invalid or expired token')
    # legacy fallback: allow simple username entry
    if not user_name:
        user_name = st.sidebar.text_input('Username', value=remembered or 'guest')
        remember_me = st.sidebar.checkbox('Remember this device', value=bool(remembered))
        if remember_me and st.sidebar.button('Save username'):
            set_last_user(user_name)
            st.sidebar.success('Username saved on this device')
        if not remember_me and st.sidebar.button('Forget saved username'):
            set_last_user('')
            st.sidebar.info('Forgot saved username')
else:
    # already have a validated session user
    st.sidebar.markdown(f"**Logged in:** {user_name}")
    remember_me = False
    # show session controls
    from services.db import list_sessions, delete_session, delete_sessions_for_user
    sid = st.session_state.get('session_id', '')
    cols = st.sidebar.columns([2,1])
    with cols[0]:
        if sid:
            st.sidebar.write(f'Session: {sid[:8]}...')
    with cols[1]:
        if sid and st.sidebar.button('Logout'):
            try:
                delete_session(sid)
            except Exception:
                pass
            st.session_state['session_id'] = ''
            st.experimental_rerun()
    # show user's active sessions and allow revoke
    try:
        my_sess = list_sessions(user_name)
        if my_sess:
            if st.sidebar.checkbox('Show my sessions'):
                for s in my_sess:
                    st.sidebar.write(f"{s.get('session_id')[:8]}... created {s.get('created_at')} expires {s.get('expires_at')}")
                if st.sidebar.button('Revoke all my sessions'):
                    deleted = delete_sessions_for_user(user_name)
                    st.sidebar.success(f'Revoked {deleted} sessions')
                    st.session_state['session_id'] = ''
                    st.experimental_rerun()
    except Exception:
        pass
# support admin impersonation stored in session state
if 'impersonate_user' in st.session_state and st.session_state.get('impersonate_user'):
    st.sidebar.markdown(f"**Impersonating:** {st.session_state['impersonate_user']}")
    current_user = st.session_state['impersonate_user']
else:
    current_user = user_name
# show admin badge in sidebar
try:
    if is_admin_user(user_name):
        st.sidebar.markdown('**Role:** ADMIN')
    else:
        st.sidebar.markdown('**Role:** User')
except Exception:
    pass
page = st.sidebar.radio("Navigate", [
    "Home",
    "Explore Destinations",
    "Hotels & Activities",
    "Recommendation Engine",
    "Overtourism Avoidance",
    "Multi-City Planner",
    "Hidden Gems",
    "Travel Cost Prediction",
    "Crowd Prediction",
    "Carbon Footprint",
    "Safety Analysis",
    "Weather Risk",
    "Sustainability",
    "Analytics Dashboard",
    "About",
    "Favorites",
])


@st.cache_data
def load_data():
    path = BASE / "dataset" / "destinations.csv"
    if path.exists():
        return pd.read_csv(path)
    return pd.DataFrame()


data = load_data()


def compute_dss(row, user_budget, selected_activities, weights=None):
    # Normalize inputs and compute a simple Destination Suitability Score (0-100)
    if weights is None:
        weights = dict(budget=0.2, interest=0.2, safety=0.2, crowd=0.15, weather=0.15, eco=0.1)
    max_budget = max(1, data['budget'].max())
    budget_match = max(0, 1 - abs(user_budget - row['budget']) / max_budget)
    # interest match: fraction of selected activities present
    activities = set(str(row.get('activities','')).split(';'))
    interest_match = 0.0
    if selected_activities:
        interest_match = len(set(selected_activities) & activities) / len(selected_activities)
    safety = row.get('womens_safety', 50) / 100.0
    crowd = (100 - row.get('crowd_index', 50)) / 100.0
    weather = (100 - row.get('weather_risk', 50)) / 100.0
    eco = row.get('eco_score', 50) / 100.0
    score = (
        weights['budget'] * budget_match +
        weights['interest'] * interest_match +
        weights['safety'] * safety +
        weights['crowd'] * crowd +
        weights['weather'] * weather +
        weights['eco'] * eco
    )
    return float(round(score * 100, 2))


if page == "Home":
    st.title("WAYPOINT — AI Powered Smart Tourism Intelligence Platform")
    st.markdown(
        "WAYPOINT recommends the BEST destination for your trip considering crowding, weather, safety, budget, sustainability and personalized preferences."
    )
    st.write("Use the sidebar to explore modules and run the Recommendation Engine.")

elif page == "Explore Destinations":
    st.header("Explore Destinations")
    st.write("Browse destinations and filter by budget, climate, country, and activities")
    st.dataframe(data.head(100))

elif page == "Hotels & Activities":
    st.header('Hotels & Activities Recommender')
    st.write('Find recommended hotels for a destination and explore suggested activities.')
    if data.empty:
        st.warning('Dataset not found. Generate dataset first.')
    else:
        dest = st.selectbox('Select destination', data['destination_name'].tolist())
        topn = st.slider('Number of hotels', 1, 10, 5)
        if st.button('Recommend Hotels'):
            from models.hotels_recommender import recommend_hotels, load_hotels
            try:
                hotels = recommend_hotels(dest, topn)
                if not hotels:
                    st.info('No hotels found for this destination.')
                else:
                    import pandas as _pd
                    st.subheader('Top hotels')
                    dfh = _pd.DataFrame(hotels)[['hotel_name','rating','price_usd','distance_km','score']]
                    st.dataframe(dfh)
            except Exception as e:
                st.error('Hotel recommendation failed: ' + str(e))
        # activities: show activities found in the dataset
        row = data[data['destination_name']==dest].iloc[0]
        acts = str(row.get('activities',''))
        if acts:
            st.subheader('Activities & Attractions')
            st.write(', '.join([a.strip() for a in acts.split(';') if a.strip()]))

elif page == "Recommendation Engine":
    st.header("Recommendation Engine")
    if data.empty:
        st.warning("Dataset not found. Run dataset/generate_dataset.py to create the data.")
    else:
        # User inputs
        col1, col2 = st.columns([2,3])
        with col1:
            user_budget = st.number_input("Estimated total budget (USD)", min_value=50, value=500)
            trip_duration = st.number_input("Trip duration (days)", min_value=1, value=5)
            num_travelers = st.number_input("Number of travelers", min_value=1, value=2)
            season = st.selectbox("Preferred season", sorted(data['best_season'].unique()))
            activities_all = sorted({a for s in data['activities'].fillna('').tolist() for a in s.split(';') if a})
            selected_activities = st.multiselect("Interests / Activities", activities_all, default=activities_all[:2])
            origin_lat = st.number_input('Your origin latitude', value=12.9716, format="%.6f")
            origin_lon = st.number_input('Your origin longitude', value=77.5946, format="%.6f")
            transport_mode = st.selectbox('Preferred transport mode', ['car','train','bus','air'])
            eco_pref = st.slider('Prefer greener options (eco weight)', 0.0, 1.0, 0.25)
        with col2:
            st.write("\n")
            st.write("Preview map of candidate destinations")
            fig = px.scatter_geo(data_frame=data.sample(min(200, len(data))), lat='latitude', lon='longitude', hover_name='destination_name', size='overall_rating', projection='natural earth')
            st.plotly_chart(fig, use_container_width=True)

        if st.button("Get Recommendations"):
            # Candidate filtering: prefer matching season and at least one activity
            candidates = data.copy()
            if season:
                candidates = candidates[candidates['best_season'] == season]
            if selected_activities:
                candidates = candidates[candidates['activities'].str.contains('|'.join(selected_activities), na=False)]
            if candidates.empty:
                candidates = data.copy()

            # Try model-based ranking first
            from models.recommender_predict import predict_scores, explain_instance, load_model as load_rec_model
            pre, model, features = load_rec_model()
            if model is not None:
                try:
                    scores = predict_scores(candidates)
                    candidates = candidates.reset_index(drop=True)
                    candidates['model_score'] = scores
                    # try to apply personalized model if available
                    try:
                        import joblib as _joblib
                        PERS_PATH = Path(__file__).parent / 'models' / 'personalized_model.joblib'
                        if PERS_PATH.exists():
                            pobj = _joblib.load(PERS_PATH)
                            pmodel = pobj.get('model')
                            pfeats = pobj.get('features', [])
                            if pmodel is not None and pfeats:
                                # safely build prediction matrix
                                Xp = candidates.reindex(columns=pfeats).fillna(0)
                                try:
                                    _probs = pmodel.predict_proba(Xp)
                                    # handle classifiers trained on single class
                                    if _probs.shape[1] == 1:
                                        classes = getattr(pmodel, 'classes_', None)
                                        if classes is not None and 1 in classes:
                                            pref_prob = _probs[:, 0]
                                        else:
                                            pref_prob = 1.0 - _probs[:, 0]
                                    else:
                                        classes = getattr(pmodel, 'classes_', None)
                                        if classes is not None and 1 in classes:
                                            pref_prob = _probs[:, int(list(classes).index(1))]
                                        else:
                                            pref_prob = _probs[:, 0]
                                    candidates['pref_prob'] = pref_prob
                                    # blend: shift by prob-0.5 scaled
                                    candidates['personalized_score'] = candidates['model_score'] + 15.0 * (candidates['pref_prob'] - 0.5)
                                except Exception:
                                    candidates['personalized_score'] = candidates['model_score']
                            else:
                                candidates['personalized_score'] = candidates['model_score']
                        else:
                            candidates['personalized_score'] = candidates['model_score']
                    except Exception:
                        candidates['personalized_score'] = candidates['model_score']
                    # compute carbon estimate per candidate if eco preference > 0
                    if eco_pref > 0:
                        from models.carbon import trip_emissions
                        carbs = []
                        for _, r2 in candidates.iterrows():
                            em = trip_emissions(origin_lat, origin_lon, float(r2['latitude']), float(r2['longitude']), mode=transport_mode, travelers=int(num_travelers), nights=int(trip_duration))
                            carbs.append(em['total_kg'])
                        candidates['carbon_kg'] = carbs
                        cmin = candidates['carbon_kg'].min()
                        cmax = candidates['carbon_kg'].max()
                        candidates['carbon_norm'] = (candidates['carbon_kg'] - cmin) / (cmax - cmin + 1e-9)
                        # adjust score: penalize carbon proportional to eco_pref
                        # apply on personalized_score when available, else model_score
                        base_col = 'personalized_score' if 'personalized_score' in candidates.columns else 'model_score'
                        candidates['adj_score'] = candidates[base_col] - eco_pref * candidates['carbon_norm'] * 30.0
                        ranked = candidates.sort_values('adj_score', ascending=False).head(10)
                    else:
                        # sort by personalized score if present
                        sort_col = 'personalized_score' if 'personalized_score' in candidates.columns else 'model_score'
                        ranked = candidates.sort_values(sort_col, ascending=False).head(10)
                    top5 = ranked.head(5)
                    st.subheader("Top 5 Destinations (model-ranked)")
                    for _, row in top5.iterrows():
                        name = row['destination_name']
                        score = float(row['model_score'])
                        st.markdown(f"**{name} — {score:.2f}**")
                        # save favorite button
                        if st.button('Save as Favorite', key=f"fav_{name}"):
                            from services.db import init_db, save_favorite, save_history
                            init_db()
                            save_favorite(name, float(score), meta={'reason': 'recommended', 'score': float(score)}, user=current_user)
                            save_history('save_favorite', name, {'score': float(score)}, user=current_user)
                            st.success('Saved to favorites')
                        # feedback buttons
                        fb_col1, fb_col2 = st.columns([1,1])
                        with fb_col1:
                            if st.button('Like', key=f"like_{name}"):
                                from services.db import init_db, save_feedback, save_history
                                init_db()
                                save_feedback(name, 'like', {'score': float(score)}, user=current_user)
                                save_history('feedback_like', name, {'score': float(score)}, user=current_user)
                                st.success('Thanks for your feedback (like)')
                        with fb_col2:
                            if st.button('Dislike', key=f"dislike_{name}"):
                                from services.db import init_db, save_feedback, save_history
                                init_db()
                                save_feedback(name, 'dislike', {'score': float(score)}, user=current_user)
                                save_history('feedback_dislike', name, {'score': float(score)}, user=current_user)
                                st.success('Thanks for your feedback (dislike)')
                        # explanation (SHAP visual + concise textual summary)
                        try:
                            from utils.explainability import explain_model as _explain_model, render_shap_waterfall_png, summarize_shap_explanation
                            X = pd.DataFrame([row[features]])
                            X_proc = pre.transform(X)
                            shap_vals = _explain_model(model, X_proc)
                            if shap_vals is not None:
                                pos, neg = summarize_shap_explanation(shap_vals, features)
                                if pos or neg:
                                    from utils.explainability import generate_consumer_sentences
                                    sentences = generate_consumer_sentences(pos, neg)
                                    if sentences:
                                        for s in sentences:
                                            st.write('- ' + s)
                                # interactive explanation option (Plotly bar chart)
                                show_inter = st.checkbox('Show interactive explanation', value=False)
                                try:
                                    import pandas as _pd
                                    import plotly.express as _px
                                    vals = shap_vals.values
                                    # shap_values may be (1,n) or (n_classes,1,n)
                                    if hasattr(vals, 'shape') and len(vals.shape) == 2:
                                        arr = vals[0]
                                    else:
                                        # fallback: try to index
                                        try:
                                            arr = vals[0]
                                        except Exception:
                                            arr = vals
                                    feat_names = features
                                    df_sh = _pd.DataFrame({'feature': feat_names, 'contribution': list(arr)})
                                    df_sh['sign'] = df_sh['contribution'].apply(lambda x: 'positive' if x>=0 else 'negative')
                                    df_sh['abs'] = df_sh['contribution'].abs()
                                    df_sh = df_sh.sort_values('abs', ascending=True).tail(8)
                                    if show_inter:
                                        fig_sh = _px.bar(df_sh, x='contribution', y='feature', orientation='h', color='sign', color_discrete_map={'positive':'#2ca02c','negative':'#d62728'}, hover_data=['contribution'])
                                        st.plotly_chart(fig_sh, use_container_width=True)
                                        try:
                                            csv_expl = df_sh.to_csv(index=False).encode('utf-8')
                                            st.download_button('Download explanation CSV', data=csv_expl, file_name=f'explanation_{name}.csv', mime='text/csv')
                                        except Exception:
                                            pass
                                        # full export (JSON) including preprocessed features and raw SHAP values
                                        try:
                                            import json
                                            proc_vals = None
                                            try:
                                                proc_vals = X_proc[0].tolist()
                                            except Exception:
                                                proc_vals = None
                                            shap_raw = None
                                            try:
                                                shap_raw = shap_vals.values.tolist()
                                            except Exception:
                                                try:
                                                    shap_raw = shap_vals.tolist()
                                                except Exception:
                                                    shap_raw = None
                                            # include model metadata and timestamp for reproducibility
                                            model_info = None
                                            try:
                                                model_info = {
                                                    'class': model.__class__.__name__ if model is not None else None,
                                                    'repr': str(model)[:200] if model is not None else None,
                                                    'path': getattr(model, 'save_path', None) or getattr(model, 'model_path', None)
                                                }
                                            except Exception:
                                                model_info = None
                                            from datetime import datetime
                                            expl_obj = {
                                                'destination': name,
                                                'features': list(feat_names),
                                                'raw_row': X.iloc[0].to_dict() if 'X' in locals() else {},
                                                'preprocessed': proc_vals,
                                                'shap_values': shap_raw,
                                                'model_info': model_info,
                                                'exported_at': datetime.utcnow().isoformat() + 'Z'
                                            }
                                            st.download_button('Download full explanation (JSON)', data=json.dumps(expl_obj).encode('utf-8'), file_name=f'explanation_full_{name}.json', mime='application/json')
                                            # option to save the explanation server-side (auditable)
                                            if st.button('Save explanation to server'):
                                                try:
                                                    saved = save_export_file(f'explanation_full_{name}.json', json.dumps(expl_obj).encode('utf-8'), user=current_user)
                                                    if saved:
                                                        st.success(f'Saved explanation to server: {saved}')
                                                    else:
                                                        st.error('Failed to save explanation to server')
                                                except Exception:
                                                    st.error('Failed to save explanation to server')
                                        except Exception:
                                            pass
                                    else:
                                        # render waterfall image as fallback
                                        img = render_shap_waterfall_png(shap_vals, row_index=0, max_display=6)
                                        if img is not None:
                                            st.image(img)
                                except Exception:
                                    # fallback to PNG waterfall
                                    img = render_shap_waterfall_png(shap_vals, row_index=0, max_display=6)
                                    if img is not None:
                                        st.image(img)
                            else:
                                raise Exception('shap explain failed')
                        except Exception:
                            # fallback reasons
                            reasons = []
                            if abs(row['budget'] - user_budget) / max(1, data['budget'].max()) < 0.2:
                                reasons.append("Within your budget")
                            if row['crowd_index'] < 50:
                                reasons.append("Less crowded than typical popular spots")
                            if row['womens_safety'] > 60:
                                reasons.append("Good safety indicators")
                            if row['weather_risk'] < 40:
                                reasons.append("Low weather risk for your dates")
                            if row['eco_score'] > 60:
                                reasons.append("Eco-friendly / sustainable option")
                            st.write("Reasons: " + (', '.join(reasons) if reasons else 'Balanced match across factors'))
                        # Optionally show emission breakdown and comparison
                        show_emission = False
                        try:
                            if 'carbon_kg' in row.index:
                                show_emission = True
                        except Exception:
                            show_emission = False

                        cols = st.columns([1,3])
                        with cols[0]:
                            st.image('https://via.placeholder.com/240x140.png?text='+name.replace(' ','+'))
                        with cols[1]:
                            st.write(f"**Location:** {row['state']}, {row['country']}")
                            st.write(f"**Estimated budget:** ${int(row['budget'])}")
                            st.write(f"**Crowd index:** {row['crowd_index']} — **Safety:** {row['womens_safety']} — **Eco:** {row['eco_score']}")
                            st.write(f"**Activities:** {row['activities']}")
                            st.write(f"**Nearby hotels occupancy:** {row.get('hotel_occupancy', 'N/A')}%")
                            if show_emission:
                                try:
                                    st.write(f"Estimated trip CO2: {row['carbon_kg']:.1f} kg")
                                    # small comparison chart
                                    import pandas as _pd
                                    import plotly.express as _px
                                    ms = float(row.get('model_score', 0))
                                    adj = float(row.get('adj_score', ms)) if 'adj_score' in row.index else ms
                                    carb = float(row.get('carbon_kg', 0))
                                    chart_df = _pd.DataFrame({'metric': ['Model score','Adjusted score','CO2 (kg)'], 'value': [ms, adj, carb]})
                                    figc = _px.bar(chart_df, x='metric', y='value', color='metric')
                                    st.plotly_chart(figc, use_container_width=True)
                                except Exception:
                                    pass
                except Exception as e:
                    st.error('Model ranking failed, falling back to heuristic. Error: ' + str(e))
                    # fallback to heuristic DSS
                    recommender = ContentRecommender(data)
                    rows = []
                    for _, r in candidates.iterrows():
                        dss = compute_dss(r, user_budget, selected_activities)
                        rows.append((r['destination_name'], dss, r))
                    rows = sorted(rows, key=lambda x: x[1], reverse=True)
                    top5 = rows[:5]
                    st.subheader('Top 5 Destinations (heuristic)')
                    for name, score, row in top5:
                        st.markdown(f"**{name} — {score}/100**")
                        st.write('Balanced match across factors')
            else:
                # no model available: fallback heuristic
                recommender = ContentRecommender(data)
                rows = []
                for _, r in candidates.iterrows():
                    dss = compute_dss(r, user_budget, selected_activities)
                    rows.append((r['destination_name'], dss, r))
                rows = sorted(rows, key=lambda x: x[1], reverse=True)
                top5 = rows[:5]
                st.subheader('Top 5 Destinations (heuristic)')
                for name, score, row in top5:
                    st.markdown(f"**{name} — {score}/100**")
                    reasons = []
                    if abs(row['budget'] - user_budget) / max(1, data['budget'].max()) < 0.2:
                        reasons.append("Within your budget")
                    if row['crowd_index'] < 50:
                        reasons.append("Less crowded than typical popular spots")
                    if row['womens_safety'] > 60:
                        reasons.append("Good safety indicators")
                    if row['weather_risk'] < 40:
                        reasons.append("Low weather risk for your dates")
                    if row['eco_score'] > 60:
                        reasons.append("Eco-friendly / sustainable option")
                    st.write("Reasons: " + (', '.join(reasons) if reasons else 'Balanced match across factors'))
                    cols = st.columns([1,3])
                    with cols[0]:
                        st.image('https://via.placeholder.com/240x140.png?text='+name.replace(' ','+'))
                    with cols[1]:
                        st.write(f"**Location:** {row['state']}, {row['country']}")
                        st.write(f"**Estimated budget:** ${int(row['budget'])}")
                        st.write(f"**Crowd index:** {row['crowd_index']} — **Safety:** {row['womens_safety']} — **Eco:** {row['eco_score']}")
                        st.write(f"**Activities:** {row['activities']}")
                        st.write(f"**Nearby hotels occupancy:** {row.get('hotel_occupancy', 'N/A')}%")

elif page == "Overtourism Avoidance":
    st.header("Overtourism Avoidance")
    st.write("Suggest nearby lower-crowd alternatives to popular spots.")
    if data.empty:
        st.warning("Dataset missing. Generate dataset first.")
    else:
        src = st.selectbox("Select crowded destination", data['destination_name'].tolist())
        max_dist = st.slider("Max distance (km)", min_value=50, max_value=2000, value=300)
        num = st.slider("Number of alternatives", min_value=1, max_value=10, value=5)
        if st.button('Suggest Alternatives'):
            from models.overtourism import suggest_alternatives
            alts = suggest_alternatives(src, data, topn=num, max_distance_km=max_dist)
            if not alts:
                st.info('No good alternatives found for this selection.')
            else:
                for a in alts:
                    st.markdown(f"**{a['destination_name']}** — Score: {a['score']} — Distance: {a['distance_km']}km — Crowd: {a['crowd_index']}")
                    st.write(f"Activities: {a['activities']}")

elif page == "Multi-City Planner":
    st.header('Smart Multi-City Planner')
    st.write('Optimize travel sequence across multiple destinations balancing distance, crowd, weather, and rating.')
    if data.empty:
        st.warning('Dataset not available. Generate dataset first.')
    else:
        names = st.multiselect('Select destinations (2-10)', data['destination_name'].tolist(), default=list(data['destination_name'].iloc[:3]))
        if len(names) < 2:
            st.info('Pick at least 2 destinations.')
        else:
            col_a, col_b = st.columns([1,1])
            with col_a:
                w_distance = st.slider('Weight: Distance', 0.0, 1.0, 0.3)
                w_crowd = st.slider('Weight: Crowd (prefer low)', 0.0, 1.0, 0.3)
            with col_b:
                w_weather = st.slider('Weight: Weather risk', 0.0, 1.0, 0.2)
                w_rating = st.slider('Weight: Rating (prefer high)', -1.0, 0.0, -0.2)
            if st.button('Plan Itinerary'):
                from models.multi_city_planner import plan_itinerary
                from models.tsp_optimizer import optimize_route
                weights = {'distance': w_distance, 'crowd': w_crowd, 'weather': w_weather, 'rating': w_rating}
                plan = plan_itinerary(names, data, weights=weights)
                use_opt = st.checkbox('Optimize route with 2-opt (reduce travel cost considering crowd/weather)')
                if 'error' in plan:
                    st.error(plan['error'])
                else:
                    ordered = plan['ordered']
                    if use_opt:
                        # prepare coords and scores
                        pts = data[data['destination_name'].isin(ordered)].set_index('destination_name').loc[ordered]
                        coords = list(zip(pts['latitude'].astype(float).tolist(), pts['longitude'].astype(float).tolist()))
                        crowd_scores = pts['crowd_index'].astype(float).tolist()
                        weather_scores = pts['weather_risk'].astype(float).tolist()
                        opt_route_idx, opt_cost = optimize_route(coords, crowd_scores=crowd_scores, weather_scores=weather_scores, alpha=w_crowd, beta=w_weather)
                        ordered = [ordered[i] for i in opt_route_idx]
                        st.write(f'Optimized route cost: {opt_cost:.1f}')
                    st.subheader('Planned sequence')
                    for i, d in enumerate(ordered):
                        st.write(f"{i+1}. {d}")
                    st.markdown(f"**Total distance:** {plan['total_distance_km']} km — **Est travel hours:** {plan['est_travel_hours']}h")
                    # map
                    try:
                        import plotly.express as px
                        pts = data[data['destination_name'].isin(plan['ordered'])]
                        pts = pts.set_index('destination_name').loc[plan['ordered']].reset_index()
                        fig = px.line_geo(pts, lat='latitude', lon='longitude', hover_name='destination_name', markers=True, projection='natural earth')
                        st.plotly_chart(fig, use_container_width=True)
                    except Exception:
                        pass

            elif page == "Travel Cost Prediction":
                st.header('Travel Cost Prediction & Budget Optimization')
                st.write('Estimate trip cost for a destination considering duration, travelers and transport factors.')
                if data.empty:
                    st.warning('Dataset missing. Generate dataset first.')
                else:
                    dest = st.selectbox('Destination', data['destination_name'].tolist())
                    trip_days = st.number_input('Trip duration (days)', min_value=1, value=5)
                    travelers = st.number_input('Number of travelers', min_value=1, value=2)
                    transport_mult = st.selectbox('Transport cost multiplier', [0.8, 1.0, 1.2, 1.5], index=1)
                    if st.button('Estimate Cost'):
                        from models.cost_predictor import load_model, predict_cost_for_destination
                        model, feats = load_model()
                        row = data[data['destination_name']==dest].iloc[0]
                        if model is None:
                            st.info('Cost model not available. Run python3 models/train_cost.py to train the model.')
                        else:
                            est = predict_cost_for_destination(row, trip_days, travelers, transport_multiplier=transport_mult)
                            st.metric('Estimated total trip cost (USD)', f"${est:,.0f}")
                            # simple breakdown
                            hotel = row['hotel_cost'] * trip_days * travelers
                            transport = row['transport_cost'] * travelers * transport_mult
                            food = row['food_cost'] * trip_days * travelers
                            activities = est - (hotel + transport + food)
                            st.write('Estimated breakdown:')
                            st.write(f"Hotel: ${hotel:,.0f}")
                            st.write(f"Transport: ${transport:,.0f}")
                            st.write(f"Food: ${food:,.0f}")
                            st.write(f"Other (activities/taxes): ${max(0, activities):,.0f}")

            elif page == "Carbon Footprint":
                st.header('Carbon Footprint Calculator')
                st.write('Estimate carbon emissions for your trip and get greener alternatives.')
                if data.empty:
                    st.warning('Dataset unavailable. Generate dataset first.')
                else:
                    origin_lat = st.number_input('Origin latitude', value=12.9716)
                    origin_lon = st.number_input('Origin longitude', value=77.5946)
                    dest = st.selectbox('Destination', data['destination_name'].tolist())
                    mode = st.selectbox('Transport mode', ['car','train','bus','air'])
                    travelers = st.number_input('Travelers', min_value=1, value=2)
                    nights = st.number_input('Nights', min_value=1, value=3)
                    if st.button('Estimate Carbon Footprint'):
                        from models.carbon import trip_emissions, greener_alternatives
                        row = data[data['destination_name']==dest].iloc[0]
                        res = trip_emissions(origin_lat, origin_lon, float(row['latitude']), float(row['longitude']), mode=mode, travelers=travelers, nights=nights)
                        st.metric('Estimated CO2 (kg)', f"{res['total_kg']:,}")
                        st.write(f"Transport: {res['transport_kg']} kg CO2 — Accommodation: {res['accommodation_kg']} kg CO2 — Distance: {res['distance_km']} km")
                        st.subheader('Greener alternatives nearby')
                        try:
                            alts = greener_alternatives(dest, data, origin_lat, origin_lon, mode=mode, travelers=travelers, nights=nights, topn=5)
                            if not alts:
                                st.write('No greener alternatives found within distance limit')
                            else:
                                for a in alts:
                                    st.write(f"{a['destination_name']} — {a['total_kg']} kg CO2 — Distance: {a['distance_km']} km — Eco: {a['eco_score']} — Crowd: {a['crowd_index']}")
                        except Exception:
                            pass

elif page == "Analytics Dashboard":
    st.header('Analytics Dashboard')
    st.write('View collected feedback and retrain the personalized model from this UI.')
    from services.db import list_feedback
    fb = list_feedback(limit=1000)
    # allow filtering by user
    users = ['All users'] + sorted({f.get('user','guest') or 'guest' for f in fb})
    sel_user = st.selectbox('Filter by user', users, index=0)
    if sel_user != 'All users':
        fb = [f for f in fb if (f.get('user') or 'guest') == sel_user]
    # audit-only view for admin events
    st.write('---')
    audit_only = st.checkbox('Show audit events only (impersonation, deletes)', value=False)
    if audit_only:
        from services.db import list_history
        events = {'impersonation_set', 'impersonation_cleared', 'delete_favorite', 'impersonation_revoked', 'admin_added', 'admin_removed', 'magic_link_created'}
        sel_event = st.selectbox('Event type', options=['All'] + sorted(events), index=0)
        actor_filter = st.text_input('Actor username (leave empty for all)', value='')
        # date range and pagination
        col_s, col_e = st.columns([1,1])
        with col_s:
            start_date = st.date_input('Start date (audit)', value=None)
        with col_e:
            end_date = st.date_input('End date (audit)', value=None)
        page_size = st.selectbox('Page size', [25,50,100,200], index=1)
        if 'audit_page' not in st.session_state:
            st.session_state['audit_page'] = 1
        page = st.session_state['audit_page']
        offset = (page - 1) * int(page_size)
        s_iso = start_date.isoformat() if start_date else None
        e_iso = end_date.isoformat() if end_date else None
        action_filter = None if sel_event == 'All' else sel_event
        user_filter = actor_filter if actor_filter else None
        hist = list_history(limit=int(page_size), offset=int(offset), start_iso=s_iso, end_iso=e_iso, action=action_filter, user=user_filter)
        # compute total pages
        try:
            from services.db import count_history
            total = count_history(start_iso=s_iso, end_iso=e_iso, action=action_filter, user=user_filter)
        except Exception:
            total = None
        total_pages = (total // int(page_size)) + (1 if total and total % int(page_size) else 0) if total is not None else None
        cols_nav = st.columns([1,1,2,1])
        with cols_nav[0]:
            if st.button('Prev'):
                if st.session_state['audit_page'] > 1:
                    st.session_state['audit_page'] -= 1
                    st.experimental_rerun()
        with cols_nav[1]:
            if st.button('Next'):
                if total_pages is None or st.session_state['audit_page'] < total_pages:
                    st.session_state['audit_page'] += 1
                    st.experimental_rerun()
        with cols_nav[2]:
            st.write(f'Page {st.session_state["audit_page"]}' + (f' of {total_pages}' if total_pages else ''))
        with cols_nav[3]:
            if st.button('Refresh'):
                st.experimental_rerun()
        # actor/user filtering is handled server-side via the `user` param
        if not hist:
            st.info('No audit events recorded for the selected filters or page.')
        else:
            import pandas as _pd
            df_a = _pd.DataFrame(hist)
            st.subheader('Audit events')
            st.dataframe(df_a[['id','created_at','user','action','destination_name','details']])
            csv = df_a.to_csv(index=False).encode('utf-8')
            st.download_button('Export audit CSV (page)', data=csv, file_name='audit_export_page.csv', mime='text/csv')
            # full export (server-side) for the current filters
            if st.button('Export full filtered set (server)'):
                try:
                    from services.db import export_history_csv, save_history
                    fname = f"history_export_{st.session_state.get('audit_page',1)}_{int(pd.Timestamp.now().timestamp())}.csv"
                    outp = export_history_csv(str(Path('data') / 'exports' / fname), start_iso=s_iso, end_iso=e_iso, action=action_filter, user=user_filter)
                    if outp:
                        with open(outp, 'rb') as f:
                            b = f.read()
                        st.download_button('Download full audit CSV', data=b, file_name=fname, mime='text/csv')
                        try:
                            save_history('export_audit', fname, {'path': outp}, user=user_name)
                        except Exception:
                            pass
                    else:
                        st.error('Failed to export audit CSV')
                except Exception:
                    st.error('Failed to export audit CSV')
            # allow one-click revoke of impersonation events
            imp_rows = [h for h in histf if h.get('action')=='impersonation_set']
            if imp_rows:
                st.write('---')
                st.write('Revoke an impersonation')
                if not is_admin_user(user_name):
                    st.error('Only admin users can revoke impersonations')
                else:
                    opts = [f"{r['id']} | {r['created_at']} | {r.get('destination_name') or r.get('user') or ''}" for r in imp_rows]
                    sel = st.selectbox('Select impersonation to revoke', options=opts)
                    if st.button('Revoke selected impersonation'):
                        sel_id = int(sel.split('|')[0].strip())
                        st.session_state['confirm_revoke'] = sel_id
                        st.experimental_rerun()
                    # confirmation
                    if st.session_state.get('confirm_revoke'):
                        crid = st.session_state.get('confirm_revoke')
                        rec = next((r for r in imp_rows if r.get('id')==crid), None)
                        if rec:
                            st.warning(f"Confirm revoke impersonation: {rec.get('destination_name') or rec.get('user') or ''} ?")
                            c1, c2 = st.columns([1,1])
                            with c1:
                                if st.button('Confirm Revoke'):
                                    try:
                                        from services.db import init_db, save_history
                                        init_db()
                                        # clear active impersonation if it matches
                                        active = st.session_state.get('impersonate_user','')
                                        target = rec.get('destination_name') or rec.get('user') or ''
                                        if active == target:
                                            st.session_state['impersonate_user'] = ''
                                        save_history('impersonation_revoked', target, {'revoked_from': rec.get('user')}, user=user_name)
                                        st.session_state['confirm_revoke'] = None
                                        st.success('Impersonation revoked')
                                        st.experimental_rerun()
                                    except Exception:
                                        st.error('Failed to revoke impersonation')
                            with c2:
                                if st.button('Cancel Revoke'):
                                    st.session_state['confirm_revoke'] = None
                                    st.info('Cancelled')
                                    st.experimental_rerun()
        st.stop()
    # Admin management (manage admins list)
    st.write('---')
    st.subheader('Admin Management')
    if not is_admin_user(user_name):
        st.write('Only admins may manage admin users.')
    else:
        from services.auth import load_admins, add_admin, remove_admin
        admins = load_admins()
        st.write('Current admins: ' + ', '.join(admins))
        new_admin = st.text_input('Add admin username', value='')
        if st.button('Add admin') and new_admin:
            ok = add_admin(new_admin)
            if ok:
                try:
                    from services.db import init_db, save_history
                    init_db()
                    save_history('admin_added', new_admin, {}, user=user_name)
                except Exception:
                    pass
                st.success(f'Added admin: {new_admin}')
                st.experimental_rerun()
            else:
                st.error('Failed to add admin (maybe already exists)')
        # remove admin
        if admins:
            sel_rem = st.selectbox('Select admin to remove', options=[''] + admins)
            if sel_rem:
                if st.button('Remove selected admin'):
                    if sel_rem == user_name:
                        st.error('Cannot remove yourself')
                    else:
                        ok = remove_admin(sel_rem)
                        if ok:
                            try:
                                from services.db import init_db, save_history
                                init_db()
                                save_history('admin_removed', sel_rem, {}, user=user_name)
                            except Exception:
                                pass
                            st.success(f'Removed admin: {sel_rem}')
                            st.experimental_rerun()
                        else:
                            st.error('Failed to remove admin')
    # impersonation controls (admin)
    if is_admin_user(user_name):
        st.write('---')
        imp = st.text_input('Impersonate username (admin only)', value='')
        col1, col2 = st.columns([1,1])
        with col1:
            if st.button('Set impersonation') and imp:
                prev = st.session_state.get('impersonate_user', '')
                st.session_state['impersonate_user'] = imp
                try:
                    from services.db import init_db, save_history
                    init_db()
                    save_history('impersonation_set', imp, {'prev': prev}, user=user_name)
                except Exception:
                    pass
                st.experimental_rerun()
        with col2:
            if st.button('Clear impersonation'):
                prev = st.session_state.get('impersonate_user', '')
                st.session_state['impersonate_user'] = ''
                try:
                    from services.db import init_db, save_history
                    init_db()
                    save_history('impersonation_cleared', prev, {}, user=user_name)
                except Exception:
                    pass
                st.experimental_rerun()
    if not fb:
        st.info('No feedback records yet. Encourage users to Like/Dislike recommendations to collect training data.')
    else:
        import pandas as _pd
        df_fb = _pd.DataFrame(fb)
        st.write('Feedback summary')
        likes = df_fb[df_fb['feedback']=='like'].shape[0]
        dislikes = df_fb[df_fb['feedback']=='dislike'].shape[0]
        st.metric('Likes', likes)
        st.metric('Dislikes', dislikes)
        st.subheader('Recent feedback')
        st.dataframe(df_fb[['id','created_at','destination_name','feedback','details']].head(200))
        # export CSV
        csv_bytes = df_fb.to_csv(index=False).encode('utf-8')
        st.download_button('Export feedback CSV', data=csv_bytes, file_name='feedback_export.csv', mime='text/csv')
        # delete selected
        ids = df_fb['id'].astype(str).tolist()
        to_delete = st.multiselect('Select feedback IDs to delete', options=ids)
        if st.button('Delete selected') and to_delete:
            from services.db import delete_feedback, init_db
            init_db()
            for fid in to_delete:
                try:
                    delete_feedback(int(fid))
                except Exception:
                    pass
            st.success(f'Deleted {len(to_delete)} feedback entries')
            st.experimental_rerun()
        # filtered export by date range
        st.write('---')
        st.write('Export filtered feedback')
        col_a, col_b = st.columns([1,1])
        with col_a:
            start_date = st.date_input('Start date', value=None)
        with col_b:
            end_date = st.date_input('End date', value=None)
        if st.button('Export filtered CSV'):
            from services.db import export_feedback_csv_filtered
            s = start_date.isoformat() if start_date else None
            e = end_date.isoformat() if end_date else None
            path = export_feedback_csv_filtered('data/feedback_export_filtered.csv', start_iso=s, end_iso=e)
            with open(path, 'rb') as f:
                data_bytes = f.read()
            st.download_button('Download filtered CSV', data=data_bytes, file_name='feedback_filtered.csv', mime='text/csv')
        # purge older than N days
        st.write('---')
        purge_days = st.number_input('Purge feedback older than (days)', min_value=1, max_value=3650, value=365)
        if st.button('Purge old feedback'):
            from services.db import delete_feedback_older_than, init_db
            init_db()
            deleted = delete_feedback_older_than(int(purge_days))
            st.success(f'Deleted {deleted} feedback entries older than {purge_days} days')
            st.experimental_rerun()
    st.write('')
    if st.button('Retrain personalized model from feedback'):
        with st.spinner('Retraining personalized model...'):
            try:
                from models.train_personalized import train
                train()
                st.success('Retraining finished. Model saved to models/personalized_model.joblib')
            except Exception as e:
                st.error('Retraining failed: ' + str(e))

    # Admin sessions management
    if is_admin_user(user_name):
        st.write('---')
        st.subheader('Admin: Manage Active Sessions')
        try:
            from services.db import list_sessions, delete_session
            all_sess = list_sessions()
            if not all_sess:
                st.write('No active sessions found.')
            else:
                import pandas as _pd
                df_s = _pd.DataFrame(all_sess)
                st.dataframe(df_s[['session_id','user','created_at','expires_at']].head(200))
                for s in all_sess:
                    cols = st.columns([3,1])
                    with cols[0]:
                        st.write(f"{s.get('session_id')[:10]}... — {s.get('user')} — created {s.get('created_at')}")
                    with cols[1]:
                        if st.button('Revoke', key=f"revoke_{s.get('session_id')}"):
                            try:
                                ok = delete_session(s.get('session_id'))
                                if ok:
                                    try:
                                        from services.db import save_history
                                        save_history('session_revoked_admin', s.get('user'), {'session': s.get('session_id')}, user=user_name)
                                    except Exception:
                                        pass
                                    st.success('Session revoked')
                                else:
                                    st.error('Failed to revoke session')
                            except Exception:
                                st.error('Failed to revoke session')
                            st.experimental_rerun()
        except Exception:
            pass

    # List saved explanation exports
    st.write('---')
    st.subheader('Saved Explanation Exports')
    try:
        from services.db import list_history, delete_export
        exports = [h for h in list_history(limit=1000) if h.get('action') == 'export_explanation']
        if not exports:
            st.info('No server-saved exports found.')
        else:
            import pandas as _pd
            df_ex = _pd.DataFrame(exports)
            st.dataframe(df_ex[['id','created_at','user','destination_name','details']].head(200))
            for ex in exports:
                ex_id = ex.get('id')
                ex_user = ex.get('user') or ''
                ex_when = ex.get('created_at')
                ex_name = ex.get('destination_name')
                ex_path = ex.get('details', {}).get('path')
                cols = st.columns([3,1,1])
                with cols[0]:
                    st.write(f"{ex_id} — {ex_name} — by {ex_user} @ {ex_when}")
                with cols[1]:
                    if ex_path and Path(ex_path).exists():
                        try:
                            with open(ex_path, 'rb') as f:
                                data_bytes = f.read()
                            st.download_button('Download', data=data_bytes, file_name=Path(ex_path).name, key=f'dl_{ex_id}')
                        except Exception:
                            st.write('File missing')
                    else:
                        st.write('File missing')
                with cols[2]:
                    if is_admin_user(user_name):
                        if st.button('Delete', key=f'del_{ex_id}'):
                            ok = delete_export(ex_id)
                            if ok:
                                st.success('Deleted export')
                            else:
                                st.error('Failed to delete export')
                            st.experimental_rerun()
                    else:
                        st.write('')
    except Exception:
        pass

elif page == "About":
    st.header("About WAYPOINT")
    st.markdown("Built with Streamlit, pandas, scikit-learn, and explainable ML techniques.")

elif page == "Crowd Prediction":
    st.header("Crowd Prediction & Overtourism Avoidance")
    st.write("Predict crowd index for a destination and suggest lower-crowd alternatives.")
    from models.crowd_prediction import load_model, predict_crowd_for_row, top_n_crowded
    model, features = load_model()
    col1, col2 = st.columns([2,3])
    with col1:
        dest = st.selectbox("Choose destination", data['destination_name'].tolist())
        num_travelers = st.number_input("Number of travelers", min_value=1, value=2)
        travel_month = st.selectbox("Travel month", ["January","February","March","April","May","June","July","August","September","October","November","December"])    
        if st.button('Predict Crowd'):
            row = data[data['destination_name'] == dest].iloc[0]
            if model is None:
                st.warning('Crowd model not found. Train it by running `python3 models/train_crowd.py`')
            else:
                pred = predict_crowd_for_row(row)
                st.metric("Predicted Crowd Index", f"{pred:.1f}/100")
                # Suggest lower-crowd alternatives within same state or country
                candidates = data[(data['country'] == row['country']) & (data['destination_name'] != dest)].copy()
                candidates['predicted'] = candidates.apply(lambda r: predict_crowd_for_row(r) if model else r['crowd_index'], axis=1)
                alternatives = candidates.sort_values('predicted').head(5)
                st.subheader('Lower-crowd Alternatives')
                for _, alt in alternatives.iterrows():
                    st.write(f"{alt['destination_name']} — Predicted crowd: {alt['predicted']:.1f} — Activities: {alt['activities']}")
    with col2:
        st.write('Crowd distribution (sample)')
        fig = px.histogram(data, x='crowd_index', nbins=20)
        st.plotly_chart(fig, use_container_width=True)
    # footfall forecast
    try:
        from models.footfall_prediction import load_model, forecast_destination_series
        ts = pd.read_csv('dataset/time_series.csv')
        hist = ts[ts['destination_name']==dest].sort_values('year_month')
        if not hist.empty:
            model, feat = load_model()
            if model is not None:
                future = forecast_destination_series(dest, hist, steps=6)
                if future:
                    last_month = hist['year_month'].iloc[-1]
                    st.subheader('6-month Footfall Forecast')
                    months = pd.date_range(start=last_month+'-01', periods=7, freq='MS')[1:]
                    df_fore = {'month': months.strftime('%Y-%m'), 'forecast': future}
                    st.line_chart(pd.DataFrame(df_fore).set_index('month'))
            else:
                st.info('Footfall forecasting model not available. Run python3 models/train_footfall.py')
    except Exception:
        pass

elif page == "Favorites":
    st.header("Favorites & History")
    from services.db import init_db, list_favorites, delete_favorite, list_history
    init_db()
    show_my_only = st.checkbox('Show only my favorites', value=True)
    favs = list_favorites(user=current_user if show_my_only else None)
    if not favs:
        st.info('No favorites saved yet. Save recommendations from the Recommendation Engine.')
    else:
        for f in favs:
            cols = st.columns([4,1])
            with cols[0]:
                st.markdown(f"**{f['destination_name']}** — Score: {f.get('score')}")
                st.write(f"Saved by: {f.get('user','guest')} — Saved at: {f['created_at']}")
            with cols[1]:
                owner = (f.get('user') or 'guest')
                is_admin = is_admin_user(user_name)
                allowed = (current_user == owner) or is_admin
                if allowed:
                    if st.button('Delete', key=f"del_{f['id']}"):
                        st.session_state['confirm_delete'] = f['id']
                        st.session_state['confirm_delete_name'] = f['destination_name']
                        st.experimental_rerun()
                else:
                    st.write('No permission to delete')

    st.subheader('Recent actions')
    show_history_my_only = st.checkbox('Show only my actions', value=True)
    hist = list_history(50, user=current_user if show_history_my_only else None)
    if not hist:
        st.write('No recent actions')
    else:
        for h in hist:
            st.write(f"[{h['created_at']}] {h['user']} — {h['action']} — {h['destination_name']} — {h['details']}")
    # deletion confirmation dialog
    if st.session_state.get('confirm_delete'):
        cid = st.session_state.get('confirm_delete')
        cname = st.session_state.get('confirm_delete_name', '')
        st.warning(f"Confirm delete favorite: {cname} ?")
        colc, cold = st.columns([1,1])
        with colc:
            if st.button('Confirm Delete'):
                from services.db import init_db, delete_favorite, save_history
                init_db()
                delete_favorite(cid)
                save_history('delete_favorite', cname or '', {}, user=current_user)
                st.session_state['confirm_delete'] = None
                st.session_state['confirm_delete_name'] = ''
                st.success('Favorite deleted')
                st.experimental_rerun()
        with cold:
            if st.button('Cancel'):
                st.session_state['confirm_delete'] = None
                st.session_state['confirm_delete_name'] = ''
                st.info('Cancelled')
                st.experimental_rerun()

else:
    st.header(page)
    st.info("Module coming soon — prototype scaffolding in place.")

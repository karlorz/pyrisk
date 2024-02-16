from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for, current_app
)
from flask import jsonify
from werkzeug.exceptions import abort
import json
import requests

from riskch.db import get_db
from riskch.compute import getTrades, calCAR, calPnl_fixfrac, calCCxy

bp = Blueprint('mpool', __name__)

@bp.route('/')
def index():
    db = get_db()
    issues = db.execute(
        'SELECT *'
        ' FROM marketpool m'
        ' ORDER BY m.id ASC'
    ).fetchall()
    return render_template('mpool/index.html', issues=issues)

@bp.route('/search')
def searchindex():
    issue = "spy"
    return redirect(url_for("mpool.search",issue=issue))

@bp.route('/<string:issue>/search', methods=('GET', 'POST'))
def search(issue):
    data = ""
    if request.method == 'POST':
        issue = request.form['issue']
    error = None
    base_url = 'https://www.alphavantage.co/query?function=SYMBOL_SEARCH&keywords='
    apikey = current_app.config["API_KEY"]
    url = f"{base_url}{issue}&apikey={apikey}"
    
    if not issue:
        error = 'Issue is required.'
        
    if error is None:
        try:
            r = requests.get(url)
            data = r.json()
            formatted_data = json.dumps(data, indent=1)
            return render_template('mpool/search.html', formatted_data=formatted_data, issue=issue)
        except requests.exceptions.RequestException as e:
            error = f"An error occurred: {str(e)}"
            return render_template('mpool/search.html', issue=issue)
    return render_template('mpool/search.html', issue=issue)

@bp.route('/create', methods=('GET', 'POST'))
def create():
    if request.method == 'POST':
        issue = request.form['issue']
        fromdate = request.form['from_date']
        todate = request.form['to_date']
        error = None

        if not issue:
            error = 'Issue is required.'
        
        if error is None:
            db = get_db()
            try:
                db.execute(
                    'INSERT INTO marketpool (issue, fromdate, todate)'
                    ' VALUES (?, ?, ?)',
                    (issue, fromdate, todate, )
                )
                db.commit()
            except db.IntegrityError:
                error = f"Issue {issue} is already in the pool."
            else:
                return redirect(url_for("mpool.index"))
        flash(error)

    return render_template('mpool/create.html')

def get_issue(id,):
    oneissue = get_db().execute(
        'SELECT *'
        ' FROM marketpool m'
        ' WHERE m.id = ?',
        (id,)
    ).fetchone()

    if oneissue is None:
        abort(404, f"Issue id {id} doesn't exist.")

    return oneissue

def get_issue_name(issue,):
    oneissue = get_db().execute(
        'SELECT *'
        ' FROM marketpool m'
        ' WHERE m.issue = ?',
        (issue,)
    ).fetchone()

    if oneissue is None:
        abort(404, f"Issue name {issue} doesn't exist.")

    return oneissue

@bp.route('/<int:id>/update', methods=('GET', 'POST'))
def update(id):
    oneissue = get_issue(id)
    preissue = oneissue["issue"]

    if request.method == 'POST':
        issue = request.form['issue']
        fromdate = request.form['from_date']
        todate = request.form['to_date']
        error = None

        if not issue:
            error = 'Issue is required.'

        if error is None:
            db = get_db()
            try:
                if issue != preissue:
                    # clear previous computation results
                    db.execute(
                        'UPDATE marketpool SET issue = ?, fromdate = ?, todate = ?, car25 = 0.0, safef = 0.0'
                        ' WHERE id = ?',
                        (issue, fromdate, todate, id)
                    )                    
                else:
                    db.execute(
                        'UPDATE marketpool SET issue = ?, fromdate = ?, todate = ?'
                        ' WHERE id = ?',
                        (issue, fromdate, todate, id)
                    )
                db.commit()
                
            except db.IntegrityError:
                error = f"Issue {issue} is already in the pool."
            else:
                return redirect(url_for("mpool.index"))
        flash(error)

    return render_template('mpool/update.html', oneissue=oneissue)

@bp.route('/<int:id>/delete', methods=('POST',))
def delete(id):
    get_issue(id)
    db = get_db()
    db.execute('DELETE FROM marketpool WHERE id = ?', (id,))
    db.commit()
    return redirect(url_for('mpool.index'))

@bp.route('/<int:id>/load', methods=('GET',))
def load(id):

    return redirect(url_for('mpool.index'))

@bp.route('/<int:id>/sim', methods=('GET',))
def sim(id):
    oneissue = get_issue(id)
    datasource = "remote"
    remoterefresh = True   
    fromdate = oneissue['fromdate']
    todate = oneissue['todate']
    error = None
    f = 0

    if fromdate is None or todate is None:
        error = "Time period is required."

    try:
        trades = getTrades(oneissue, datasource, remoterefresh)
        pnl_d = trades["pnl_d"]
        close_d = trades["close_d"]
    except Exception as e:
        error = str(e)
    else:
        result = calCAR(pnl_d,oneissue)
        f = int(result['safef'])
        pnl = calPnl_fixfrac(pnl_d,oneissue,f)
  
    if error is not None:
        flash(error)
    else:
        db = get_db()
        # update car25, safef
        db.execute(
            'UPDATE marketpool SET car25 = ?, safef = ?'
            ' WHERE id = ?',
            (result['car25'], f, id)
        )
        id =int(id)
        # delete previous simulation curves
        db.execute(
            'DELETE FROM eq_safef WHERE issue_id = ?',(id,)
        )        
        # insert new simulation curves
        list_data = result['eq']
        for curve in list_data:
            json_str = json.dumps(curve)
            db.execute(
                'INSERT INTO eq_safef (issue_id, curve) VALUES (?, ?)', 
                (id, json_str))

        # delete previous histogram
        db.execute(
            'DELETE FROM hist WHERE issue_id = ?',(id,)
        ) 

        # insert histogram and trade curve at safe
        tradeno = 0
        for element in pnl:
            if tradeno == 0:
                db.execute(
                    'INSERT INTO hist (issue_id, trade_id, close_d, retrun_d, pnl)'
                    'VALUES (?, ?, ?, ?, ?)', 
                    (id, tradeno, close_d[tradeno], 0, element)
                )  
            else:
                db.execute(
                    'INSERT INTO hist (issue_id, trade_id, close_d, retrun_d, pnl)'
                    'VALUES (?, ?, ?, ?, ?)', 
                    (id, tradeno, close_d[tradeno], pnl_d[tradeno-1], element)
                )
            tradeno += 1
            
        # Retrieve pnl bench id 1
        #benchmark_name = "spy"
        oneissue_benchid = 1
        #oneissue_bench = get_issue_name(benchmark_name)
        
        try:
            pnl_bench = db.execute('SELECT pnl FROM hist WHERE issue_id = ?', (oneissue_benchid,)).fetchall()
            pnl_bench_list = [row[0] for row in pnl_bench]
            correlation = calCCxy(pnl,pnl_bench_list)
            # update correlation to benchmark
            db.execute(
                'UPDATE marketpool SET cor2bench = ?'
                ' WHERE id = ?',
                (correlation, id)
            )
        except Exception as e:
            error = str(e)
            flash(error)
        
        db.commit()

    return redirect(url_for('mpool.index'))
from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for
)
import json

from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for
)
from riskch.db import get_db
from riskch.mpool import get_issue

from flask import Blueprint

bp = Blueprint("chart", __name__, url_prefix="/chart")

@bp.route('/')
def index():
    return redirect(url_for("index"))

@bp.route("/sim/<int:id>", methods=('GET',))
def simchart(id):
    db = get_db()

    # Generate data for each line 
    num_lines = 10
    data = []
    result = []

    result = db.execute(
        'SELECT curve'
        ' FROM eq_safef'
        ' WHERE issue_id = ?'
        ' ORDER BY RANDOM() LIMIT ?',
        (id,num_lines,)
    ).fetchall()
    
    if len(result) > 0:
        for i in range(num_lines):
            json_str = result[i][0]
            line_data = json.loads(json_str)
            data.append(line_data)
            if True and 1+1 == 3: #print result
                print ("line_data: ", line_data)          
            
            labels = list(range(1, len(line_data)+1))
    else:
        return redirect(url_for("index"))
    
    # Return the components to the HTML template
    return render_template(
        template_name_or_list='chart/index.html',
        data=data,
        labels=labels,
        num_lines=num_lines
    )
    
@bp.route("/hist/<int:id>", methods=('GET',))
def hist(id):
    data = []
    db = get_db()
    oneissue = get_issue(id)
    # Retrieve pnl
    pnl = db.execute('SELECT pnl FROM hist WHERE issue_id = ?', (id,)).fetchall()
    pnl_list = [row[0] for row in pnl]
    labels = list(range(1, len(pnl_list)+1))
    data.append(pnl_list)
    # Retrieve daily close
    close_d = db.execute('SELECT close_d FROM hist WHERE issue_id = ?', (id,)).fetchall()
    close_list = [row[0] for row in close_d]    
    data.append(close_list)
    # Return the components to the HTML template
    return render_template(
        template_name_or_list='chart/hist.html',
        data=data,
        labels=labels,
        num_lines=1,
        oneissue=oneissue
    )
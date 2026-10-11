import asyncio
import copy
import json
from pathlib import Path
from types import SimpleNamespace

from sqlalchemy import select
from backend.core.db.models import AnalysisStatus, Product
from backend.core.db.session import SessionLocal
from backend.services.analysis_service import attach_catalog_products, recommendations_for

BASE = dict(skin_type='dry', age_group='25_34', skin_sensitivity='low',
            known_product_allergy='no', severe_irritation='no', sunscreen_frequency='every_day')

def candidate(eye=0, face=0, eligible=True, quality=1):
    return SimpleNamespace(status=AnalysisStatus.completed, image_quality_score=quality, result={
        'recommendation_gate': {'eligible': eligible},
        'model_output': {'prediction_version':'audit-synthetic-v1', 'confidence': {
            'calibration_status':'calibrated', 'calibration_version':'audit-synthetic-v1'}},
        'derived_score': {'score_version':'audit-synthetic-v1', 'roi_version':'audit-synthetic-v1',
            'regions': {name:dict(score=min(100,pixels/5),wrinkle_pixels=pixels,evaluated_pixels=10000)
                        for name,pixels in [('image_right_periocular',eye),('forehead',face)]}}})

async def main():
    async with SessionLocal() as session:
        products = (await session.scalars(select(Product))).all()
    rows=[]
    def run(label, analysis, answers=None, budget=None, expected_eye=None):
        result=recommendations_for(analysis, BASE if answers is None else answers)
        attach_catalog_products(result, products, market='TH', max_price_satang=budget)
        items=result['recommendations']
        eye_items=[i for i in items if i['rule_id']=='R-WRINKLE-EYE-001']
        if expected_eye is not None:
            assert bool(eye_items)==expected_eye, label
        for item in eye_items:
            assert all('eye_contour' in p['application_regions'] for p in item['products']), label
        rows.append(dict(case=label,status=result['status'],blocked_reason=result.get('blocked_reason'),
            image_context=result['image_context'],
            recommendations=[dict(rule=i['rule_id'], products=[p['name'] for p in i.get('products',[])]) for i in items]))
        return result
    for skin in ['dry','normal','combination','oily']:
        for sensitivity in ['low','medium']:
            r=run(f'eligible_eye_5pct_{skin}_{sensitivity}',candidate(eye=500),
                  {**BASE,'skin_type':skin,'skin_sensitivity':sensitivity},expected_eye=True)
            assert next(i for i in r['recommendations'] if i['rule_id']=='R-WRINKLE-EYE-001')['products']
    for pixels in [0,100,165,181,182,200,335,1000]:
        run(f'eye_boundary_{pixels}/10000',candidate(eye=pixels),expected_eye=pixels>=182)
    run('forehead_only',candidate(face=500),expected_eye=False)
    r=run('eye_and_forehead',candidate(eye=1000,face=500),expected_eye=True)
    assert [i['rule_id'] for i in r['recommendations'][:2]]==['R-WRINKLE-EYE-001','R-WRINKLE-FACE-001']
    run('gate_withheld',candidate(eye=500,eligible=False),expected_eye=False)
    run('low_quality',candidate(eye=500,quality=.79),expected_eye=False)
    run('under_18',candidate(eye=500),{**BASE,'age_group':'13_17'},expected_eye=False)
    run('age_missing',candidate(eye=500),{k:v for k,v in BASE.items() if k!='age_group'},expected_eye=False)
    run('sensitivity_high',candidate(eye=500),{**BASE,'skin_sensitivity':'high'},expected_eye=False)
    run('allergy_reported',candidate(eye=500),{**BASE,'known_product_allergy':'yes'},expected_eye=False)
    r=run('budget_500_baht',candidate(eye=500),budget=50000,expected_eye=True)
    assert not next(i for i in r['recommendations'] if i['rule_id']=='R-WRINKLE-EYE-001')['products']
    run('budget_1000_baht',candidate(eye=500),budget=100000,expected_eye=True)
    for label in ['hero','hopper','astronaut','blank']:
        record=json.loads(Path('/tmp/audit-'+label+'.json').read_text())
        obj=SimpleNamespace(status=AnalysisStatus(record['status']),image_quality_score=record.get('image_quality_score'),result=record.get('result'))
        run('live_image_'+label,obj,expected_eye=False)
        if label in ['hero','hopper']:
            diagnostic=copy.deepcopy(obj)
            diagnostic.result['derived_score']=diagnostic.result['experimental_score']
            diagnostic.result['recommendation_gate']={'eligible':True}
            r=run('counterfactual_gate_only_'+label,diagnostic,expected_eye=label=='hero')
            target='R-WRINKLE-EYE-001' if label=='hero' else 'R-WRINKLE-FACE-001'
            assert next(i for i in r['recommendations'] if i['rule_id']==target)['products']
    print(json.dumps(dict(catalog_count=len(products),
        eye_product_count=sum('eye_contour' in (p.application_regions or []) for p in products),
        cases=rows,assertions='passed'),ensure_ascii=False,indent=2))

asyncio.run(main())

from phase1_analyze import EVIDENCE_ZH as ORIGINAL
EVIDENCE_ZH={**ORIGINAL,
 'E_181':'鼻塞或流清鼻涕',
 'E_208':'BMI低于18.5或体重过低',
 'E_78':'过量饮酒或酒精依赖',
 'E_217':'平躺时症状加重、坐起时缓解'}
def describe(group_id,items):
 answer={'Yes':'是','No':'否'}.get(items[0]['answer_en'],items[0]['answer_en'])
 return EVIDENCE_ZH.get(group_id,items[0]['question_en'])+'：'+answer

import json
T="transpose=2"
G={
"1-coche-y-viajes":[("coche-mirada-primer-plano","n072708.mp4",0,6.5),("coche-dormida","n095206.mp4",1,8),("coche-al-volante","volante.mp4",0,6),("coche-copiloto","copiloto.mp4",0,3.5),("coche-mirada","mirada-coche.mp4",0,3),("carretera-amanecer","n071657.mp4",1,5)],
"2-playa":[("playa-amanecer-explora","n073352.mp4",3,7),("playa-sol-sobre-el-mar","n073352.mp4",24,5),("playa-rocas-amanecer","n074121.mp4",12,7),("playa-carrera-lateral","n111911.mp4",10.5,3),("playa-en-la-orilla","n111911.mp4",19,3.5),("playa-corre-camara-lenta","playa.mp4",0,2.8,{"speed":0.7})],
"3-campo-y-naranjal":[("campo-hierba-corre-hacia-ti","n172020.mp4",12,11),("naranjal-camino-atardecer","v174524.mp4",5,6),("naranjal-atardecer-02","v174616.mp4",0,6),("cielo-atardecer","v174636.mp4",0,5),("naranjal-olfatea","v174705.mp4",2,6),("naranjal-olfatea-02","v174648.mp4",0,5),("paseo-pov-naranjal","a2v083140.mp4",1,6),("paseo-te-mira","a2v084342.mp4",22,7),("paseo-carretera-pov","a2v094310.mp4",0,10),("trote-feliz","trote.mp4",0,3.7)],
"4-casa-y-terraza":[("terraza-salto-bienvenida","v173554.mp4",1.5,4),("llegada-a-casa-llaves","a2v103655.mp4",14,9),("bebe-agua","a2v103740.mp4",14,9),("asomada-cortina","a2v103740.mp4",26,5),("comiendo","a2v104257.mp4",5,9),("sofa-mirada","a2v115012.mp4",3,6),("espera-comida","espera.mp4",0,3.2),("lazo-navidad","d0008.mov",0,8,{"pre":T}),("lazo-navidad-02","d0010.mov",0,8,{"pre":T}),("panuelo-calabaza","d0001.mov",0,6,{"pre":T})],
"5-con-el-gato":[("gato-mirada-fija","n101205.mp4",9.5,4),("alyha-celosa-del-gato","n101205.mp4",24.5,6),("gato-bostezo","n101325.mp4",24,3.5,{"zoom":1.6,"focus":[0.6,0.95]}),("gato-en-la-silla","n101132.mp4",14,7),("gato-y-alyha","gato.mp4",17,4),("gato-se-acerca","gato.mp4",27,4)],
"6-rio-y-montana":[("rio-sendero-pov","n152742.mp4",0,12),("rio-rocas-pov-te-mira","n153339.mp4",6,6),("rio-entre-piedras","n153339.mp4",12,8),("rio-en-el-agua","n153414.mp4",23.5,4),("rio-al-otro-lado","n153414.mp4",0,7),("rio-mirador","n154159.mp4",0,3),("montana-paisaje","n154231.mp4",0,5)],
}
for g,cl in G.items():
    sc=[]
    for c in cl:
        d={"type":"video","src":c[1],"start":c[2],"len":c[3]}
        if len(c)>4: d.update(c[4])
        sc.append(d)
    json.dump({"name":g,"scenes":sc,"labels":[c[0] for c in cl]},open(f"{g}.json","w"),ensure_ascii=False)

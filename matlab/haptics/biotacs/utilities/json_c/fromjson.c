//Pulled from https://github.com/christianpanton/matlab-json

#include "mex.h"
#include <json/json.h>
#include <stdio.h>
#include <string.h>


void object(json_object * jo, mxArray ** mxa); 
void parse(json_object * jo, mxArray ** mxa); 

void mexFunction (int nlhs, mxArray* plhs[], int nrhs, const mxArray* prhs[])
{

    char *buf;
    mwSize buflen;

    if (nrhs != 1) { 
        mexErrMsgTxt("One input argument required.");

    } 
    if (nlhs > 1) {
        mexErrMsgTxt("Too many output arguments.");
    }

    if (!mxIsChar(prhs[0]) || (mxGetM(prhs[0]) != 1 ) )  {
        mexErrMsgTxt("Input argument must be a string.");
    }

    buflen = mxGetN(prhs[0])*sizeof(mxChar)+1;
    buf = mxMalloc(buflen);

    mxGetString(prhs[0], buf, buflen); 

    json_object * jo = json_tokener_parse(buf);

    if(is_error(jo))
        mexErrMsgTxt("error parsing json.");
    else
        parse(jo, &plhs[0]);
    

}



void value(json_object *jo, mxArray ** mxa){

    enum json_type type = json_object_get_type(jo);
    mxArray *ma; 
    int32_t *ptmp;

    switch (type) {
        case json_type_boolean: 
            ma = mxCreateLogicalScalar(json_object_get_boolean(jo));
            break;
        case json_type_double: 
            ma = mxCreateDoubleScalar(json_object_get_double(jo));
            break;
        case json_type_int: 
            ma = mxCreateNumericMatrix(1, 1, mxINT32_CLASS, mxREAL);
            *((int32_t *)mxGetData(ma)) = json_object_get_int(jo);
            ma = mxCreateDoubleScalar(json_object_get_double(jo));
            break;
        case json_type_string: 
            ma = mxCreateString(json_object_get_string(jo));
            break;
    }

    *mxa = ma;

}

void array( json_object *jo, char *key, mxArray ** mxa) {

    enum json_type type;
    int i;

    json_object *jv;
    json_object *ja = jo; 

    mxArray *ma;

    if(key){ 
        ja = json_object_object_get(jo, key);
    }

    int len = json_object_array_length(ja); 

    *mxa = mxCreateCellMatrix(len, 1);

    for (i=0; i< len; i++){

        jv = json_object_array_get_idx(ja, i); 

        if(jv){
            type = json_object_get_type(jv);

            if (type == json_type_array) {
                array(jv, NULL, &ma);
            }

            else if (type != json_type_object) {
                value(jv, &ma);
            }

            else {
                object(jv, &ma);
            }
        }
        else{
            ma = mxCreateDoubleScalar(mxGetNaN());
        }

        mxSetCell(*mxa, i, ma);

    }
}

int keys_count(json_object * jo){

    int count = 0;
    
    json_object_object_foreach(jo, key, val)
        count++;

    return count;
}

void keys_fill(json_object * jo, char *** keys, int count){

    int i = 0;
    *keys = mxMalloc(count * sizeof(*keys));

    json_object_object_foreach(jo, key, val){
        (*keys)[i] = mxMalloc(sizeof(char)*(strlen(key)+1));       
        strcpy((*keys)[i], key);
        i++;
    }
}

void object(json_object * jo, mxArray ** mxa) {

    enum json_type type;
    char ** keys;
    mxArray *ma;

    int i;
    int count = keys_count(jo); 

    keys_fill(jo, &keys, count);

    *mxa = mxCreateStructMatrix(1, 1, count, (const char**) keys);

    json_object_object_foreach(jo, key, val) {

        if(val){
            type = json_object_get_type(val);

            switch (type) {
                case json_type_boolean:
                case json_type_double:
                case json_type_int:
                case json_type_string:
                    value(val, &ma);
                    break;
                case json_type_object: 
                    object(json_object_object_get(jo, key), &ma);
                    break;
                case json_type_array: 
                    array(jo, key, &ma);
                    break;
            }
        }
        else{
            ma = mxCreateDoubleScalar(mxGetNaN());
        }

        mxSetField(*mxa, 0, key, ma);

    }
}


void parse(json_object * jo, mxArray ** ma) {

    enum json_type type;
    if(jo){    
    
        type = json_object_get_type(jo);

        switch (type) {
            case json_type_boolean:
            case json_type_double:
            case json_type_int:
            case json_type_string:
                value(jo, ma);
                break;
            case json_type_object: 
                object(jo, ma);
                break;
            case json_type_array: 
                array(jo, NULL, ma);
                break;
        }
    }else{
        *ma = mxCreateDoubleScalar(mxGetNaN());
    }
}



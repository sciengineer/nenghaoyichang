def return_tuple(a):

    return (a,a+1,a-1)

print(str(return_tuple(1)))

with open('predict.txt', 'w+') as f_predict:



    f_predict.write(str(return_tuple(1)))

with open('predict.txt', 'r') as f_predict:



    a = f_predict.read()
    print(a)
    predict = tuple(eval(a))
    print(predict)
    print(type(predict))
    a,b,c = predict
    print(a)
    print(type(a))

#     # a = f_predict.read()
#     # print(f_predict.read())
#     predict = f_predict.read()
#     print(predict)
    # print(predict[0])

# with open('test.txt', 'w+') as f_predict:
#
#
#
#     f_predict.write('b')
#
# with open('test.txt', 'r+') as f_predict:
#     # f_predict.write('b')
#
#     a = f_predict.read()
#     print(a)


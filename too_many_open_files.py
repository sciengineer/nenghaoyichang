
for i in range(2000):
    fp = open('files/file_%d' % i, 'w+')
    fp.write(str(i))
    fp.close()

fps = []
for x in range(2000):
    h = open('files/file_%d' % x, 'r+')
    print (h.read())
    fps.append(h)


# with open('num'+str(123)+'.txt', 'w') as f:
#     f.write('1')
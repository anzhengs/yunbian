# 行优先
def getRowList(zeroX, zeroY, zeroZ, ynum):
    RowAll = []
    for y in range(ynum):
        a = zeroX - y * 27
        b = zeroY + y * 25
        c = zeroZ - y * 1
        Row = [a, b, c]
        RowAll.append(Row)
    print(RowAll)
    return RowAll


# 列优先
def getColumnList(zeroX, zeroY, zeroZ, xnum):
    ColumnAll = []
    for x in range(xnum):
        a = zeroX + x * 26
        b = zeroY + x * 25
        c = zeroZ + x * 1
        Column = [a, b, c]
        ColumnAll.append(Column)
    return ColumnAll


# 行优先（Z次序）
def z_row(zeroX, zeroY, zeroZ, xnum, ynum, znum):
    xyzList1 = []
    print(zeroX, zeroY, zeroZ, xnum, ynum, znum)
    RowList = getRowList(zeroX, zeroY, zeroZ, ynum)
    for z in range(znum):
        for x in range(xnum):
            for y in range(ynum):
                listP = [RowList[y][0] + x * 28, RowList[y][1] + x * 26, RowList[y][2] + z * 20]
                xyzList1.append(listP)

    print('RowList', RowList)
    print('xyzList1', xyzList1)
    return xyzList1


# 行优先（S次序）
def s_row(zeroX, zeroY, zeroZ, xnum, ynum, znum):
    xyzList = []
    RowList = getRowList(zeroX, zeroY, zeroZ, ynum)
    for z in range(znum):
        for x in range(xnum):
            for y in range(ynum):
                if x % 2 == 0:
                    listP = [RowList[y][0] + x * 26.5, RowList[y][1] + x * 25.5, RowList[y][2] + z * 20]
                    xyzList.append(listP)
                else:
                    RowList_reverse = RowList[::-1]
                    listP = [RowList_reverse[y][0] + x * 26.5, RowList_reverse[y][1] + x * 25.5, RowList[y][2] + z * 20]
                    xyzList.append(listP)
    return xyzList


# 列优先（Z次序）
def z_column(zeroX, zeroY, zeroZ, xnum, ynum, znum):
    xyzList = []
    ColumnList = getColumnList(zeroX, zeroY, zeroZ, xnum)
    for z in range(znum):
        for y in range(ynum):
            for x in range(xnum):
                listP = [ColumnList[x][0] - y * 27, ColumnList[x][1] + y * 25, ColumnList[x][2] + z * 20]
                xyzList.append(listP)
    return xyzList


# 列优先（S次序）
def s_column(zeroX, zeroY, zeroZ, xnum, ynum, znum):
    xyzList = []
    ColumnList = getColumnList(zeroX, zeroY, zeroZ, xnum)
    for z in range(znum):
        for y in range(ynum):
            for x in range(xnum):
                if y % 2 == 0:
                    listP = [ColumnList[x][0] - y * 27, ColumnList[x][1] + y * 25, ColumnList[x][2] + z * 20]
                    xyzList.append(listP)
                else:
                    ColumnList_reverse = ColumnList[::-1]
                    listP = [ColumnList_reverse[x][0] - y * 27, ColumnList_reverse[x][1] + y * 25,
                             ColumnList[x][2] + z * 20]
                    xyzList.append(listP)
    return xyzList


def getXYZList(ranks, order, X, Y, Z, xNumOne, yNumOne, zNumOne):
    ranks = 1
    order = 1
    X, Y, Z = 2, 2, 2
    coords = []
    if ranks == 1 and order == 1:
        coords = z_row(X, Y, Z, xNumOne, yNumOne, zNumOne)
        print(coords)
    elif ranks == 1 and order == 2:
        coords = s_row(X, Y, Z, xNumOne, yNumOne, zNumOne)
    elif ranks == 2 and order == 1:
        coords = z_column(X, Y, Z, xNumOne, yNumOne, zNumOne)
    elif ranks == 2 and order == 2:
        coords = s_column(X, Y, Z, xNumOne, yNumOne, zNumOne)
    return coords

# XYZ = [54.8, 177.3, 145.0]
# ranks, order, xNumOne, yNumOne, zNumOne = 1, 1, 2, 3, 2
# a = getXYZList(ranks, order, XYZ[0], XYZ[1], XYZ[2], xNumOne, yNumOne, zNumOne)
# b = a[::-1]
# print(b)
# print(b[len(a)-1])

# a = z_column(250, 10, 150, 2, 2, 2)
# b = s_column(250, 10, 150, 2, 2, 2)
# c = s_row(250, 10, 150, 2, 2, 2)
# d = z_row(250, 10, 150, 2, 2, 2)
# print(a)
# print(b)
# print(c)
# print(d)

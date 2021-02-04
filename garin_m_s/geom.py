# -*- coding: utf-8 -*-

def point_between_points(point_start, point_end, point_find):
    """
    Опеределяет нахождение точки на плоскости между двумя точками.

    :param point_start: точка старта.
    :param point_end: точка окончания.
    :param point_find: определяемая точка.
    :return: True если point_find находится на плоскости между point_start и point_end.
    """
    if point_start[0] >= point_end[0] and point_start[1] >= point_end[1]:
        if point_start[0] >= point_find[0] >= point_end[0] and point_start[1] >= point_find[1] >= point_end[1]:
            return True
    elif point_start[0] <= point_end[0] and point_start[1] <= point_end[1]:
        if point_start[0] <= point_find[0] <= point_end[0] and point_start[1] <= point_find[1] <= point_end[1]:
            return True
    elif point_start[0] >= point_end[0] and point_start[1] <= point_end[1]:
        if point_start[0] >= point_find[0] >= point_end[0] and point_start[1] <= point_find[1] <= point_end[1]:
            return True
    elif point_start[0] <= point_end[0] and point_start[1] >= point_end[1]:
        if point_start[0] <= point_find[0] <= point_end[0] and point_start[1] >= point_find[1] >= point_end[1]:
            return True


def distance_between_points(point_1, point_2):
    """
    Определение расстояние между точками.

    :param point_1: точка № 1.
    :param point_2: точка № 2.
    :return: расстояние между точками.
    """
    import math

    return math.sqrt((point_2[0] - point_1[0]) ** 2 + (point_2[1] - point_1[1]) ** 2)


def point_between_on_distance(distance, point_start, point_end):
    """
    Определяет точку на отрезке на указанном расстоянии.

    :param distance: необходимая дистанция.
    :param point_start: точка отрезка от которой ищется точка.
    :param point_end: конечная точка отрезка.
    :return: координаты точки, лежащей на отрезке между point_start и point_end на расстоянии distance от point_start.
    """
    import math

    z = (point_end[0] - point_start[0]) ** 2 + (point_end[1] - point_start[1]) ** 2
    distance_now = math.sqrt(z)
    k = distance / distance_now
    x = point_start[0] + (point_end[0] - point_start[0]) * k
    y = point_start[1] + (point_end[1] - point_start[1]) * k

    return x, y


def point_on_a_line_2(coord_x, line):

    coord_y = (line[2] - line[0] * coord_x) / line[1]

    return coord_x, coord_y


def line_on_a_plane(point_1, point_2):
    """
    Составление общего уравнения прямой на плоскости: A * x + B * y = C.
    Прямая проходит через две известные точки.

    :param point_1: координаты точки № 1.
    :param point_2: координаты точки № 2.
    :return: значения для уравнения: A, B, C.
    """

    x_1 = point_1[0]                # Координата x точки № 1
    y_1 = point_1[1]                # Координата y точки № 1
    x_2 = point_2[0]                # Координата x точки № 2
    y_2 = point_2[1]                # Координата y точки № 2

    a_x = (x_2 - x_1)               # Координата вектора x
    a_y = (y_2 - y_1)               # Координата вектора y

    return a_y, - a_x, - a_x * y_1 + a_y * x_1


def line_on_a_plane_perpendicular(point, line):
    """
    Составление общего уравнения прямой на плоскости: A * x + B * y = C.
    Прямая проходит через известную точку и перпендикулярна известной прямой.

    :param point: координаты точки.
    :param line: значения общего уравнения известной прямой на плоскости: A, B.
    :return: значения для уравнения: A, B, C.
    """

    x_0 = point[0]
    y_0 = point[1]
    a_x = line[1] * - 1
    a_y = line[0]

    return a_x, a_y, a_x * x_0 + a_y * y_0


def line_on_a_plane_parallel(point, line):
    """
    Составление общего уравнения прямой на плоскости: A * x + B * y = C.
    Прямая проходит через известную точку и параллельна известной прямой.

    :param point: координаты точки.
    :param line: значения общего уравнения известной прямой на плоскости: A, B, C.
    :return: значения для уравнения: A, B, C.
    """

    x_0 = point[0]
    y_0 = point[1]
    a_x = line[0]
    a_y = line[1]

    return a_x, a_y, a_x * x_0 + a_y * y_0


def intersection_line_line(line_1, line_2):
    """
    Находит точку пересечения двух прямых на плоскости.
    Способ нахождения: решение системы линейных уравнений (общее уравнение прямой на плоскости).

    :param line_1: значения общего уравнения известной прямой на плоскости: A, B, C.
    :param line_2: значения общего уравнения известной прямой на плоскости: A, B, C.
    :return: координаты точки пересечения.
    """
    import numpy

    m = numpy.array([[line_1[0], line_1[1]], [line_2[0], line_2[1]]])
    v = numpy.array([line_1[2], line_2[2]])
    point_2 = numpy.linalg.lstsq(m, v)
    # print('Новый вариант: ', point_2)
    # print('Новый вариант _ 2: ', point_2[0])
    # point = numpy.linalg.solve(m, v)
    # print(point)
    return tuple(point_2[0])


def intersection(point_start, point_end, point_find):
    """
    Находит близжащую точку от точки на плоскости на прямой между двумя точками.

    :param point_start: точка старта прямой.
    :param point_end: точка окончания прямой.
    :param point_find: точка на плоскости.
    :return: координаты близжащей точки от point_find на прямой между двумя point_start и point_end.
    """
    line = line_on_a_plane(point_1=point_start, point_2=point_end)
    perpendicular = line_on_a_plane_perpendicular(point=point_find, line=line)
    return intersection_line_line(line_1=line, line_2=perpendicular)


def points_on_ring(scene, radius, point_base, center, count, edge=0):
    """
    Определяет точки на половине окружности к точке на плоскости.

    :param scene: площадь плоскости.
    :param radius: радиус окружности
    :param point_base: точка относительно которой определяется перпендикуляр разеляющий окружность
    :param center: центр окружности
    :param count: количество точек на полукруге.
    :return: кортеж точек на половине окружности.
    """
    local_count = (count + 1) // 2
    if local_count != (count + 1) / 2:
        raise ValueError('Допускается нечётное число от 3 (трёх).')
    else:
        points = []
        line_to_target = line_on_a_plane(point_1=point_base, point_2=center)
        perpendicular = line_on_a_plane_perpendicular(point=center, line=line_to_target)

        line_ox = line_on_a_plane(point_1=(3, 0), point_2=(6, 0))
        intersection = intersection_line_line(line_1=perpendicular, line_2=line_ox)

        points.append(point_between_on_distance(distance=radius, point_start=center, point_end=point_base))
        points.append(point_between_on_distance(distance=radius, point_start=center, point_end=intersection))
        points.append(point_between_on_distance(distance=-radius, point_start=center, point_end=intersection))

        distance_between = distance_between_points(point_1=points[0], point_2=points[1]) / (local_count - 1)
        for point in points[1:3]:
            for i in range(local_count - 2):
                dist = distance_between * (i + 1)
                point = point_between_on_distance(distance=dist, point_start=points[0], point_end=point)
                point = point_between_on_distance(distance=radius, point_start=center, point_end=point)
                if edge < point[0] < scene[0] - edge and edge < point[1] < scene[1] - edge:
                    points.append(point)
        for point in points[:]:
            if edge < point[0] < scene[0] - edge and edge < point[1] < scene[1] - edge:
                pass
            else:
                points.remove(point)

        return tuple(points)
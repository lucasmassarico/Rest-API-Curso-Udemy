from flask_restful import Resource, reqparse
from flask import request, abort
from models.hotel import HotelModel
from flask_jwt_extended import jwt_required
from marshmallow import Schema, fields
from marshmallow.validate import Length
from resources.filtros import normalize_path_params, consulta_com_cidade, consulta_sem_cidade
import sqlite3


class HoteisQuerySchema(Schema):
    estrelas_min = fields.Float()
    estrelas_max = fields.Float()
    diaria_min = fields.Float()
    diaria_max = fields.Float()
    cidade = fields.String()
    # cidade = fields.String(required=True, validate=Length(max=30, error="cidade must be a 'string' shorter than '30' letters."))
    limit = fields.Float()
    offset = fields.Float()


class HoteisAPI(Resource):
    def get(self):
        # conecta ao BD
        connection = sqlite3.connect('instance/banco.db')
        cursor = connection.cursor()

        # valida os args
        schema = HoteisQuerySchema()
        errors = schema.validate(request.args)
        if errors:
            abort(400, errors)

        # tive que usar o request.args porque não estava funcionando pelo reqparse, como no curso
        # descobri outra forma de resolver, que seria adicionar no .add_argument(location="args")
        args = request.args.to_dict()
        parametros = normalize_path_params(**args)

        if not args.get('cidade'):
            consulta = consulta_sem_cidade
            tupla = tuple([parametros[chave] for chave in parametros])
            resultado = cursor.execute(consulta, tupla)
        else:
            consulta = consulta_com_cidade
            tupla = tuple([parametros[chave] for chave in parametros])
            resultado = cursor.execute(consulta, tupla)
        hoteis = []
        for linha in resultado:
            hoteis.append({
                'hotel_id': linha[0],
                'nome': linha[1],
                'estrelas': linha[2],
                'diaria': linha[3],
                'cidade': linha[4],
                'site__id': linha[5]
            })

        return {'hoteis': hoteis}


class Hotel(Resource):
    atributos = reqparse.RequestParser()
    atributos.add_argument('nome', type=str, required=True, help="The field 'nome cannot be left blank.")
    atributos.add_argument('estrelas', type=float, required=True, help="The field 'estrelas' cannot be left blank.")
    atributos.add_argument('diaria')
    atributos.add_argument('cidade')
    atributos.add_argument('site_id', type=int, required=True, help="Every 'hotel' needs to be linked with a site")

    def get(self, hotel_id):
        hotel = HotelModel.find_hotel(hotel_id)
        if hotel:
            return hotel.json()
        return {"message": "Hotel not found."}, 404

    @jwt_required()
    def post(self, hotel_id):
        if HotelModel.find_hotel(hotel_id):
            return {"message": "Hotel id '{}' already exists.".format(hotel_id)}, 400

        dados = Hotel.atributos.parse_args()
        hotel = HotelModel(hotel_id, **dados)
        try:
            hotel.save_hotel()
        except:
            return {'message': 'An internal error occurred trying to save hotel.'}, 500
        return hotel.json()

    @jwt_required()
    def put(self, hotel_id):
        dados = Hotel.atributos.parse_args()
        hotel_encontrado = HotelModel.find_hotel(hotel_id)
        if hotel_encontrado:
            hotel_encontrado.update_hotel(**dados)
            hotel_encontrado.save_hotel()
            return hotel_encontrado.json(), 200
        hotel = HotelModel(hotel_id, **dados)
        try:
            hotel.save_hotel()
        except:
            return {'message': 'An internal error occurred trying to save hotel.'}, 500
        return hotel.json(), 201

    @jwt_required()
    def delete(self, hotel_id):
        hotel = HotelModel.find_hotel(hotel_id)
        if hotel:
            try:
                hotel.delete_hotel()
            except:
                return {'message': 'An error occurred trying to delete hotel.'}, 500
            return {'message': 'Hotel deleted.'}
        return {'message': 'Hotel not found.'}, 404

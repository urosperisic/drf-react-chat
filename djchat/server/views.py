from django.db.models import Count
from rest_framework import viewsets
from rest_framework.exceptions import AuthenticationFailed, ValidationError
from rest_framework.response import Response

from .models import Server
from .schema import server_list_docs
from .serializer import ServerSerializer


class ServerListViewSet(viewsets.ViewSet):
    """
    A viewset for listing Server instances with various filtering and annotation options.

    Allows filtering by category, authenticated user membership, server ID, and quantity.
    Can also include the number of members for each server.
    """

    queryset = Server.objects.all()

    @server_list_docs
    def list(self, request):
        """
        Retrieves a list of servers based on the provided query parameters.

        This method supports multiple filtering and customization options for retrieving
        a subset of server records. It can filter servers by category, user membership,
        specific server ID, and limit the number of results returned. Additionally, it can
        annotate each server with the number of members if requested.

        Query Parameters:
            category (str, optional):
                Filters servers by the name of their associated category.
                Example: `?category=Gaming`

            qty (int, optional):
                Limits the number of servers returned in the response.
                Example: `?qty=10`

            by_user (bool, optional):
                If set to `true`, filters servers to only include those where the
                authenticated user is a member.
                Requires authentication.
                Example: `?by_user=true`

            by_serverid (str or int, optional):
                Filters to a specific server by its ID. If the server does not exist,
                a ValidationError is raised.
                Requires authentication.
                Example: `?by_serverid=42`

            with_num_members (bool, optional):
                If set to `true`, includes the number of members in each server
                by annotating the queryset with a `num_members` field.
                Example: `?with_num_members=true`

        Returns:
            rest_framework.response.Response:
                A serialized list of servers matching the query parameters. If
                `with_num_members` is true, each serialized server will include a
                `num_members` field indicating how many members belong to that server.

        Raises:
            AuthenticationFailed:
                Raised if `by_user` or `by_serverid` is provided and the user is
                not authenticated.

        ValidationError:
                - Raised if `by_serverid` is provided and does not match any existing server.
                - Raised if `by_serverid` contains an invalid (non-integer) value.

        Examples:
        Get all servers in a specific category:
            GET /api/servers/?category=Gaming

        Get a maximum of 5 servers and include number of members:
            GET /api/servers/?qty=5&with_num_members=true

        Get servers where the authenticated user is a member:
            GET /api/servers/?by_user=true

        Get a specific server by ID:
            GET /api/servers/?by_serverid=42

        Combine filters (e.g., category and num_members):
            GET /api/servers/?category=Education&with_num_members=true
        """

        category = request.query_params.get("category")
        qty = request.query_params.get("qty")
        by_user = request.query_params.get("by_user") == "true"
        by_serverid = request.query_params.get("by_serverid")
        with_num_members = request.query_params.get("with_num_members") == "true"

        if category:
            self.queryset = self.queryset.filter(category__name=category)

        if by_user:
            if by_user and request.user.is_authenticated:
                user_id = request.user.id
                self.queryset = self.queryset.filter(member=user_id)
            else:
                raise AuthenticationFailed()

        if with_num_members:
            self.queryset = self.queryset.annotate(num_members=Count("member"))

        if by_serverid:
            if not request.user.is_authenticated:
                raise AuthenticationFailed()

            try:
                self.queryset = self.queryset.filter(id=by_serverid)
                if not self.queryset.exists():
                    raise ValidationError(detail=f"Server with id {by_serverid} not found")
            except ValueError:
                raise ValidationError(detail="Server value error")

        if qty:
            self.queryset = self.queryset[: int(qty)]

        serializer = ServerSerializer(self.queryset, many=True, context={"num_members": with_num_members})
        return Response(serializer.data)


# class ServerListViewSet(viewsets.ViewSet):
#     # Removed class-level 'queryset' to avoid modifying shared state across requests

#     def list(self, request):
#         # Use a local variable instead of self.queryset to avoid thread-safety issues
#         queryset = Server.objects.all()

#         # Optional filtering by category name
#         category = request.query_params.get("category")
#         if category:
#             queryset = queryset.filter(category__name=category)

#         serializer = ServerSerializer(queryset, many=True)
#         return Response(serializer.data)

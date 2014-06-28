# encoding: utf-8
"""
nlri.py

Created by Thomas Mangin on 2012-07-08.
Copyright (c) 2009-2013 Exa Networks. All rights reserved.
"""

from struct import unpack
from exabgp.protocol.family import SAFI
from exabgp.protocol.ip.address import Address
from exabgp.protocol.ip.inet import Inet
from exabgp.bgp.message.direction import IN
from exabgp.bgp.message.notification import Notify

from exabgp.bgp.message.update.nlri.prefix import mask_to_bytes


class NLRI (Address):
	_known = dict()

	def index (self):
		return '%s%s%s' % (self.afi,self.safi,self.pack())

	# remove this when code restructure is finished
	def pack (self):
		raise Exception('unimplemented')

	@classmethod
	def register (cls):
		cls._known['%d/%d' % (cls.AFI,cls.SAFI)] = cls

	@classmethod
	def unpack (cls,afi,safi,data,addpath,nexthop,action):
		key = '%d/%d' % (afi,safi)
		if key in cls._known:
			cls._known[key].unpack(afi,safi,data,addpath,nexthop,action)

	@staticmethod
	def _nlri (afi,safi,bgp,action):
		labels = []
		rd = ''

		mask = ord(bgp[0])
		bgp = bgp[1:]

		if SAFI(safi).has_label():
			while bgp and mask >= 8:
				label = int(unpack('!L',chr(0) + bgp[:3])[0])
				bgp = bgp[3:]
				mask -= 24  	# 3 bytes
				# The last 4 bits are the bottom of Stack
				# The last bit is set for the last label
				labels.append(label>>4)
				# This is a route withdrawal
				if label == 0x800000 and action == IN.withdrawn:
					break
				# This is a next-hop
				if label == 0x000000:
					break
				if label & 1:
					break

		if SAFI(safi).has_rd():
			mask -= 8*8  # the 8 bytes of the route distinguisher
			rd = bgp[:8]
			bgp = bgp[8:]

		if mask < 0:
			raise Notify(3,10,'invalid length in NLRI prefix')

		if not bgp and mask:
			raise Notify(3,10,'not enough data for the mask provided to decode the NLRI')

		size = mask_to_bytes.get(mask,None)
		if size is None:
			raise Notify(3,10,'invalid netmask found when decoding NLRI')

		if len(bgp) < size:
			raise Notify(3,10,'could not decode route with AFI %d sand SAFI %d' % (afi,safi))

		network,bgp = bgp[:size],bgp[size:]
		padding = '\0'*(Inet.length[afi]-size)
		prefix = network + padding

		return labels,rd,mask,size,prefix,bgp
